# ports.py
"""
Gestion des ports, découverte multicast, création de sessions et
authentification optionnelle (callbacks assignés par Chats).

Principes appliqués :
- Structure fidèle à ton design original (Utilisateur, Appareil, Session, Chats)
- Pas d'historique dans Appareil (historique uniquement dans Session)
- Un seul flag d'authentification dans Session : `authentique`
- Callbacks d'authentification (demander_preuve, fournir_preuve, confirmer_preuve)
  sont des attributs de Session et sont assignés par Chats.
- Découverte multicast active par défaut ; message multicast de 1470 octets
  avec exactement la structure demandée.
- Code de connexion (8 caractères) généré uniquement après qu'un port libre
  ait été réservé pour l'utilisateur.
- Appropriation d'une chaîne multicast avec backoff aléatoire, max 2 essais.
- Paquets et CRC gérés via paquets.py (ton module).
"""

import socket
import threading
import time
import secrets
import random
from typing import List, Optional, Callable, Tuple

import paquets  # ton module fourni contenant charger_octets / decharger_octets / CRCError

# -------------------------------------------------------------------
# Constantes et configuration (modifiable si nécessaire)
# -------------------------------------------------------------------

# Alphabet base64 custom (confirmé)
BASE64_CUSTOM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?"

# Plage multicast privée (301 adresses)
base = "239.192.{}"
adresses_multicast: List[str] = []
for troisieme in range(1, 3):
    for quatrieme in range(1, 256):
        if len(adresses_multicast) >= 301:
            break
        adresses_multicast.append(base.format(f"{troisieme}.{quatrieme}"))

# Ports d'écoute "préférés" (ordre d'essai pour bind)
ports_decoutes = [
    54321, 58732, 61248, 49876, 52413,
    59987, 63254, 50789, 57801, 64523
]

# Multicast par défaut
MULTICAST_GROUP_DEFAULT = "239.192.1.1"
MULTICAST_PORT = 54321

# Durées (choisies pour LAN, ajustables)
MULTICAST_LISTEN_INTERVAL = 0.12   # temps d'écoute court pour vérifier si une chaîne est "libre"
BACKOFF_MAX = 0.08                 # backoff max (doit être < MULTICAST_LISTEN_INTERVAL)
APPROPRIATION_ATTEMPTS = 2         # max 2 essais de réservation d'une chaîne
ANNOUNCE_INTERVAL = 0.6            # intervalle d'annonce si on possède une chaîne
SOCKET_RECV_BUFFER = 2048

# Paquets de handshake (littéraux utilisés, pas d'attributs Session)
SESSION_REQUEST = b"PORTS_SESSION_REQ"
SESSION_ACK = b"PORTS_SESSION_ACK"

# Multicast message format sizes (en octets)
NOMS_SIZE = 200
PRENOMS_SIZE = 200
TAILLE_CLE_SIZE = 2
CLE_PUB_MAX = 1024
INFOS_SUP_SIZE = 40
CRC_SIZE = 4
MULTICAST_MSG_SIZE = NOMS_SIZE + PRENOMS_SIZE + TAILLE_CLE_SIZE + CLE_PUB_MAX + INFOS_SUP_SIZE + CRC_SIZE
# -------------------------------------------------------------------


# -----------------------
# Fonctions utilitaires
# -----------------------
def encode_connexion_code(ip: str, port: int, alphabet: str = BASE64_CUSTOM) -> str:
    """
    Encode IP (dotted quad) + port en un code de 8 caractères selon l'alphabet custom.
    32 bits IP + 16 bits port = 48 bits -> 8 blocs de 6 bits.
    """
    if ip == "localhost":
        octets = [127, 0, 0, 1]
    else:
        octets = [int(x) for x in ip.split(".")]
    bits = "".join(format(b, "08b") for b in octets) + format(port, "016b")
    blocs = [bits[i * 6:(i + 1) * 6] for i in range(8)]
    return "".join(alphabet[int(b, 2)] for b in blocs)


def decode_connexion_code(code: str, alphabet: str = BASE64_CUSTOM) -> Tuple[str, int]:
    """
    Décode un code de 8 caractères en (ip, port).
    """
    if len(code) != 8:
        raise ValueError("Le code doit faire 8 caractères.")
    bits = "".join(format(alphabet.index(c), "06b") for c in code)
    A = int(bits[0:8], 2)
    B = int(bits[8:16], 2)
    C = int(bits[16:24], 2)
    D = int(bits[24:32], 2)
    port = int(bits[32:48], 2)
    return f"{A}.{B}.{C}.{D}", port


# -----------------------
# Classes principales
# -----------------------

class Utilisateur:
    """
    Représente un utilisateur (local ou distant).
    - cle_privee n'est présente que pour l'utilisateur local (trappe).
    - cle_publique peut être renseignée pour tous (local ou distant).
    - authentique : indique si le pair a été authentifié PAR MOI.
    """
    def __init__(self, noms: List[str], prenoms: List[str],
                 cle_privee: Optional[bytes] = None,
                 cle_publique: Optional[bytes] = None):
        self.noms = noms
        self.prenoms = prenoms
        self.cle_privee = cle_privee
        self.cle_publique = cle_publique
        # Flag : est-ce que CE pair a été validé par moi ?
        # (True si j'ai confirmé la preuve reçue)
        self.authentique = False

    def est_local(self) -> bool:
        """Retourne True si cet utilisateur possède une clé privée (donc local)."""
        return self.cle_privee is not None

    def set_cle_publique(self, cle_pub: bytes):
        self.cle_publique = cle_pub

    def is_authenticated(self) -> bool:
        return self.authentique


class Appareil:
    """
    Représente un autre appareil sur le réseau.
    Pas d'historique ici : l'historique appartient à Session.
    """
    def __init__(self, ip: str, port: int, ut: Utilisateur):
        self.ip = ip
        self.port = port
        self.ut = ut
        # socket de réception utilisée pour envoyer/recevoir paquets vers/depuis cet appareil.
        # On crée ici une socket simple si nécessaire ; la gestion fine des sockets revient à Session/Chats.
        self.sock_recep = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class Session:
    """
    Représente une session entre deux appareils. Contient l'historique pour l'UI,
    les files d'envoi/réception, le flag `authentique` (indiquant si le pair
    a été authentifié par moi), et les callbacks d'authentification.
    """

    def __init__(self, sock_local: socket.socket, destinataire: Appareil,
                 fdc: Optional[Callable] = None, cle: Optional[bytes] = None):
        # socket local (déjà bindé par l'appelant)
        self.cet_appareil = sock_local
        self.destinataire = destinataire
        # chiffrement optionnel (fonction et clé)
        self.fdc = fdc
        self.cle = cle

        # historique pour l'UI (format brut paquets.py)
        self.octets_envoyes: List[bytes] = []
        self.octets_recus: List[bytes] = []

        # files internes
        from queue import Queue
        self.octets_a_envoyer = Queue()
        self.octets_a_recevoir = Queue()

        # état
        self.session_active = False
        # flag unique : est-ce que le pair a été authentifié PAR MOI ?
        self.authentique = False

        # Callbacks d'authentification (attributs assignés par Chats si nécessaire)
        # Signatures attendues (convention) :
        # - demander_preuve(session) -> bool
        #     Doit provoquer l'envoi d'un challenge au pair, attendre la preuve,
        #     appeler confirmer_preuve si nécessaire et renvoyer True si le pair est validé.
        # - fournir_preuve(session, challenge: bytes) -> bytes
        #     Doit utiliser la clé privée locale pour produire la preuve (signature/MAC)
        #     et renvoyer les octets de preuve. L'envoi peut être fait ici ou dans demander_preuve.
        # - confirmer_preuve(session, preuve: bytes, cle_publique_peer: bytes) -> bool
        #     Doit vérifier cryptographiquement la preuve et renvoyer True si valide.
        self.demander_preuve: Optional[Callable] = None
        self.fournir_preuve: Optional[Callable] = None
        self.confirmer_preuve: Optional[Callable] = None

        # thread d'envoi (démarré à la demande)
        self._thread_envoi = None
        self._stop_threads = False

    # -------------------------
    # Envoi / réception de données
    # -------------------------
    def envoyer_octets(self, octets: bytes, tdc: bytes = b'\x00', infos_sup: bytes = b'\x00\x00\x00\x00'):
        """
        Embarque les octets via paquets.charger_octets et envoie chaque paquet vers le destinataire.
        Met à jour l'historique octets_envoyes.
        """
        paq_list = paquets.charger_octets(octets, self.fdc if self.fdc is not None else paquets.NotImplemented,
                                          self.cle if self.cle is not None else b'', tdc, infos_sup)
        for p in paq_list:
            self.cet_appareil.sendto(p, (self.destinataire.ip, self.destinataire.port))
        self.octets_envoyes.append(octets)

    def recevoir_octets(self, paquets_list: List[bytes]):
        """
        Reconstitue les octets via paquets.decharger_octets et met à jour l'historique.
        """
        octets = paquets.decharger_octets(paquets_list, paquets.NotImplemented, b'')
        self.octets_recus.append(octets)
        return octets

    def thread_envoi(self):
        """
        Thread d'envoi : consomme octets_a_envoyer et appelle envoyer_octets.
        """
        def _run():
            from queue import Empty
            while not self._stop_threads:
                try:
                    data = self.octets_a_envoyer.get(timeout=0.5)
                    self.envoyer_octets(data)
                except Exception:
                    continue
        self._thread_envoi = threading.Thread(target=_run, daemon=True)
        self._thread_envoi.start()

    # -------------------------
    # Sécurité / création de session
    # -------------------------
    def _echange_cle(self):
        """
        Échange Diffie-Hellman minimaliste.
        Utilise la socket locale pour envoyer/recevoir A/B.
        Retourne la clé secrète (bytes).
        """
        # Valeurs p et g doivent provenir de ton contexte global si nécessaire.
        # Ici on délègue au même algorithme simple déjà présent dans d'autres fichiers.
        # Pour rester fidèle au design précédent, on réutilise la logique minimale.
        a = secrets.randbelow(paquets.__dict__.get('p', 0xFFFFFFFF)) if hasattr(paquets, 'p') else secrets.randbelow(1 << 256)
        A = pow(paquets.__dict__.get('g', 2) if hasattr(paquets, 'g') else 2, a, paquets.__dict__.get('p', (1 << 2048) - 1))
        # envoyer A
        self.cet_appareil.sendto(A.to_bytes((A.bit_length() + 7) // 8, 'big'),
                                 (self.destinataire.ip, self.destinataire.port))
        # recevoir B
        data, _ = self.cet_appareil.recvfrom(4096)
        B = int.from_bytes(data, 'big')
        K = pow(B, a, paquets.__dict__.get('p', (1 << 2048) - 1))
        return K.to_bytes((K.bit_length() + 7) // 8, 'big')

    def creer_session(self, initiateur: bool = True, timeout: float = 1.0):
        """
        Créer/initialiser la session. La logique d'ACK (SESSION_REQUEST/SESSION_ACK)
        est gérée par la classe Chats lors de la création active/passive.
        Ici on part du principe que la socket locale est prête et que le handshake
        initial (SESSION_REQUEST/SESSION_ACK) vient d'être réalisé par Chats.
        Ensuite :
          - si fdc et cle absent, on peut quand même établir la session
          - si échange de clé requis : _echange_cle()
          - ensuite, si les callbacks sont fournis, on exécute demander_preuve (optionnel)
        initiateur : True si on est l'initiateur (créateur) de la session
        """
        # Échange de clé (facultatif)
        if self.fdc is not None:
            try:
                # obtenir clé secrète via DH et la stocker éventuellement dans self.cle
                cle_secrete = self._echange_cle()
                self.cle = cle_secrete
            except Exception:
                # si DH échoue, on peut continuer mais sans chiffrement
                self.cle = None

        # Authentification (optionnelle) : exécuter les callbacks si définis.
        # Convention :
        # - demander_preuve(session) -> bool (True si pair authentifié)
        # - fournir_preuve(session, challenge: bytes) -> bytes
        # - confirmer_preuve(session, preuve: bytes, cle_publique_peer: bytes) -> bool
        try:
            if self.demander_preuve is not None:
                # On délègue la procédure complète à la fonction fournie (implémentation extérieure).
                # Elle doit renvoyer True si la preuve du pair est valide et False sinon.
                result = self.demander_preuve(self)
                self.authentique = bool(result)
            else:
                # Pas de callback : authentification non réalisée
                self.authentique = False
        except Exception:
            self.authentique = False

        self.session_active = True
        # démarrer thread d'envoi si l'utilisateur veut (optionnel)
        self.thread_envoi()

    def get_historique(self) -> dict:
        """Renvoie l'historique sous forme utile pour l'UI."""
        return {
            'envoyes': list(self.octets_envoyes),
            'recus': list(self.octets_recus),
            'authentique': bool(self.authentique)
        }

    def close(self):
        """Ferme proprement la session (threads, sockets non fermés automatiquement)."""
        self._stop_threads = True
        self.session_active = False
        # Ne ferme pas la socket locale ici : caller décide


class Chats:
    """
    Gestion des sessions multiples, découverte multicast par défaut,
    appropriation d'une chaîne multicast, création de sessions via code
    ou via découverte.
    """

    def __init__(self, ip: str, multicast_active: bool = True, include_code_in_hello: bool = True):
        self.ip = ip
        self.sessions: List[Session] = []
        self.chaine_multicast: Optional[str] = None
        self.code_connexion: Optional[str] = None
        self.contenu_chaines: List[Optional[bytes]] = [None] * len(adresses_multicast)
        self.include_code_in_hello = include_code_in_hello

        # Socket d'écoute des chaînes multicast (bind sur un des ports_decoutes)
        self.sock_de_recherche = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_de_recherche.settimeout(0.1)
        bound = False
        for p in ports_decoutes:
            try:
                self.sock_de_recherche.bind((self.ip, p))
                bound = True
                break
            except OSError:
                continue
        if not bound:
            raise OSError("Aucun port d'écoute disponible parmi ports_decoutes")

        # Rejoindre les groupes multicast
        try:
            for adresse in adresses_multicast:
                mreq = socket.inet_aton(adresse) + socket.inet_aton(self.ip)
                self.sock_de_recherche.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception:
            # Si l'OS n'autorise pas l'ajout massif, on ignore et on continuera à écouter certaines adresses.
            pass

        # Thread d'actualisation des chaînes (détection passive) : actif par défaut
        self._stop_mon = False
        if multicast_active:
            self._monitor_thread = threading.Thread(target=self.actualiser_contenu_chaines, daemon=True)
            self._monitor_thread.start()

        # Thread d'écoute des demandes de session (handshake passif)
        self._incoming_thread = threading.Thread(target=self._incoming_listener, daemon=True)
        self._incoming_thread.start()

    # -------------------------
    # Multicast : écoute / appropriation / publication
    # -------------------------
    def actualiser_contenu_chaines(self):
        """
        Écoute en permanence les chaînes multicast et met à jour self.contenu_chaines.
        Le message attendu a exactement MULTICAST_MSG_SIZE octets (1470).
        """
        while not self._stop_mon:
            try:
                data, (ip_src, port_src) = self.sock_de_recherche.recvfrom(SOCKET_RECV_BUFFER)
                # On ne force pas l'analyse complète ici : on stocke la payload brute
                # L'interface ou une fonction dédiée pourra parser ce format (taille clé, etc.)
                # On met à jour la première chaîne disponible correspondante si possible
                # Pour simplicité, on stocke l'info à l'indice correspondant si on peut trouver une adresse connue
                # Ici on ne fait pas mapping IP->indice ; on stocke les messages en FIFO (remplissage simple)
                # plus tard tu peux fournir une méthode de parsing et mapping précis.
                # Parcours pour stocker dans le premier None
                stored = False
                for i in range(len(self.contenu_chaines)):
                    if self.contenu_chaines[i] is None:
                        self.contenu_chaines[i] = data
                        stored = True
                        break
                if not stored:
                    # écrase la plus vieille
                    self.contenu_chaines[0] = data
            except socket.timeout:
                continue
            except Exception:
                continue

    def _is_chain_quiet(self, adresse_multicast: str, duree: float) -> bool:
        """
        Vérifie si une adresse multicast reçoit du trafic pendant `duree` secondes.
        On crée un socket temporaire pour écouter sur cette adresse. Si aucun paquet
        n'est reçu pendant `duree`, la chaîne est considérée "libre".
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(duree)
            # join that multicast on local interface
            try:
                mreq = socket.inet_aton(adresse_multicast) + socket.inet_aton(self.ip)
                s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                # si échec, on continue mais on ne peut garantir la détection fine
                pass
            try:
                s.recvfrom(1024)
                return False  # trafic détecté
            except socket.timeout:
                return True
        finally:
            try:
                s.close()
            except Exception:
                pass

    def trouver_chaine_multicast(self) -> Optional[str]:
        """
        Tente d'approprier une chaîne multicast libre.
        Procédure :
          - parcours des adresses multicast
          - pour chaque candidate, vérifier si la chaîne est silencieuse (durée courte)
          - si silencieuse : envoyer sur la chaîne ses informations (message format 1470)
          - écouter un intervalle plus court ; si on voit un autre message => collision
          - si pas de collision : on prend la chaîne
          - backoff aléatoire (<= BACKOFF_MAX) si collision, refaire jusqu'à APPROPRIATION_ATTEMPTS
        Retourne l'adresse multicast choisie ou None si échec.
        """
        for adresse in adresses_multicast:
            # test silence initial
            try:
                quiet = self._is_chain_quiet(adresse, MULTICAST_LISTEN_INTERVAL)
            except Exception:
                quiet = False
            if not quiet:
                continue

            # tentative d'appropriation (max 2 essais)
            for attempt in range(APPROPRIATION_ATTEMPTS):
                # envoyer nos infos sur la chaîne (payload construit par publier_message_sur_chaine)
                try:
                    self.publier_message_sur_chaine_onadresse(adresse)
                except Exception:
                    pass

                # écouter une très courte période pour détecter collision
                time.sleep(MULTICAST_LISTEN_INTERVAL / 2.0)
                # si on détecte un message issu d'un autre hôte -> collision
                # Pour simplifier : on ré-appellera _is_chain_quiet et si pas quiet -> collision
                try:
                    still_quiet = self._is_chain_quiet(adresse, MULTICAST_LISTEN_INTERVAL / 2.0)
                except Exception:
                    still_quiet = False

                if still_quiet:
                    # chaîne adoptée
                    self.chaine_multicast = adresse
                    # démarrer broadcast périodique
                    t = threading.Thread(target=self._broadcast_loop, args=(adresse,), daemon=True)
                    t.start()
                    return adresse
                else:
                    # collision : backoff aléatoire < BACKOFF_MAX puis retenter
                    backoff = random.random() * BACKOFF_MAX
                    time.sleep(backoff)
                    continue
        # aucune chaîne disponible
        return None

    def _broadcast_loop(self, adresse: str):
        """
        Envoi régulier (ANNOUNCE_INTERVAL) de l'annonce sur la chaîne que l'on possède.
        Le message respecte la structure 1470 octets.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ttl = 1
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        except Exception:
            pass
        while self.chaine_multicast == adresse:
            try:
                payload = self._build_multicast_payload()
                sock.sendto(payload, (adresse, MULTICAST_PORT))
            except Exception:
                pass
            time.sleep(ANNOUNCE_INTERVAL)
        try:
            sock.close()
        except Exception:
            pass

    def _build_multicast_payload(self) -> bytes:
        """
        Construit exactement le message multicast de 1470 octets :
        [Noms:200][Prenoms:200][taille_cle:2][cle_pub:1024][infos_sup:40][CRC:4]
        - Si la clé publique n'est pas fournie (taille=0), on place 0 dans les 2 octets,
          et on peut laisser 1024 octets de padding (zéros) après.
        - Les 40 octets infos_sup sont laissés vides pour l'instant.
        - CRC calculé sur tout sauf le champ CRC final (dernier 4 octets).
        """
        # Récupérer info locale (si on a une session / utilisateur local)
        # Ici on ne connaît pas directement l'utilisateur local : c'est géré par l'application.
        # Pour compatibilité, on place des champs vides par défaut. L'UI / application pourra
        # surcharger cette méthode si nécessaire.
        noms = b"\x00" * NOMS_SIZE
        prenoms = b"\x00" * PRENOMS_SIZE
        taille_cle = (0).to_bytes(2, 'big')
        cle_pub = b"\x00" * CLE_PUB_MAX
        infos = b"\x00" * INFOS_SUP_SIZE
        pack = noms + prenoms + taille_cle + cle_pub + infos
        crc = paquets.__dict__.get('binascii', None)
        # calc CRC en utilisant binascii.crc32 si disponible
        try:
            import binascii as _b
            crc4 = _b.crc32(pack).to_bytes(4, 'big')
        except Exception:
            crc4 = b"\x00" * 4
        return pack + crc4

    def publier_message_sur_chaine_onadresse(self, adresse: str):
        """
        Envoie le message d'annonce sur `adresse` une seule fois.
        Utilise la même construction que _build_multicast_payload.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            payload = self._build_multicast_payload()
            sock.sendto(payload, (adresse, MULTICAST_PORT))
        finally:
            try:
                sock.close()
            except Exception:
                pass

    # -------------------------
    # Création de session par code (active)
    # -------------------------
    def creer_session_par_code(self, code: str, fdc: Optional[Callable] = None, cle: Optional[bytes] = None,
                               require_discovery: bool = False, retry: int = 3, timeout: float = 0.5):
        """
        Décode le code -> (ip, port), effectue handshake (SESSION_REQUEST -> SESSION_ACK),
        crée une Session liée à une socket locale nouvellement bindée (port réservé),
        assigne les callbacks d'authentification à la session (si désiré), puis appelle
        session.creer_session() pour faire DH + auth (selon callbacks).
        """
        ip_dest, port_dest = decode_connexion_code(code)

        # Préparer socket local (port attribué dynamiquement par OS)
        sock_local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_local.bind((self.ip, 0))
        local_port = sock_local.getsockname()[1]

        # Envoi SESSION_REQUEST et attente SESSION_ACK (retry)
        sock_local.settimeout(timeout)
        for attempt in range(retry):
            try:
                sock_local.sendto(SESSION_REQUEST, (ip_dest, port_dest))
                data, _ = sock_local.recvfrom(64)
                if data == SESSION_ACK:
                    # handshake réussi
                    break
            except socket.timeout:
                continue
        else:
            sock_local.close()
            raise ConnectionError("Pas de réponse à SESSION_REQUEST")

        # Création Appareil + Session
        # Utilisateur temporaire (Inconnu) : l'application doit mettre à jour après auth
        utilisateur_temp = Utilisateur(["Inconnu"], ["Inconnu"], cle_privee=None, cle_publique=None)
        appareil = Appareil(ip_dest, port_dest, utilisateur_temp)
        session = Session(sock_local, appareil, fdc, cle)

        # Assignation des callbacks d'authentification (par défaut None)
        # L'application qui utilise Chats peut attribuer ici des callbacks spécifiques.
        # Exemple (à faire côté applicatif) :
        # session.demander_preuve = some_callable
        # session.fournir_preuve = some_callable2
        # session.confirmer_preuve = some_callable3

        # Démarrer la session (DH + auth via callbacks si fournis)
        session.creer_session(initiateur=True)
        self.sessions.append(session)
        return session

    # -------------------------
    # Incoming listener : réponse passive à SESSION_REQUEST
    # -------------------------
    def _incoming_listener(self):
        """
        Écoute en permanence les SESSION_REQUEST entrants sur sock_de_recherche.
        Lorsqu'une demande est reçue, on envoie SESSION_ACK, puis on crée une session
        associée et on lance session.creer_session() en mode passif.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.bind((self.ip, 0))  # socket arbitraire pour réponse
        except Exception:
            s = self.sock_de_recherche
        s.settimeout(0.5)
        while True:
            try:
                data, (ip_src, port_src) = self.sock_de_recherche.recvfrom(1024)
                if data == SESSION_REQUEST:
                    # envoyer ACK
                    try:
                        s.sendto(SESSION_ACK, (ip_src, port_src))
                    except Exception:
                        pass

                    # Préparer socket local pour la session (nouveau port)
                    sock_local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock_local.bind((self.ip, 0))
                    # créer Appareil & Session
                    utilisateur_temp = Utilisateur(["Inconnu"], ["Inconnu"], cle_privee=None, cle_publique=None)
                    appareil = Appareil(ip_src, port_src, utilisateur_temp)
                    session = Session(sock_local, appareil)
                    # callbacks laissés None par défaut ; l'application peut les assigner
                    # lancer la procédure de création (passive)
                    session.creer_session(initiateur=False)
                    self.sessions.append(session)
            except socket.timeout:
                continue
            except Exception:
                continue

    # -------------------------
    # Gestion codes de connexion
    # -------------------------
    def generer_code_connexion(self, port_libre: int) -> str:
        """
        Génère le code de connexion à partir de l'IP local et d'un port libre
        (port_libre doit être un port réellement réservé par l'application).
        """
        return encode_connexion_code(self.ip, port_libre)

    # -------------------------
    # Utilitaires
    # -------------------------
    def liste_sessions_actives(self) -> List[Session]:
        return [s for s in self.sessions if s.session_active]

    def close_all(self):
        # ferme proprement toutes les sessions
        for s in list(self.sessions):
            try:
                s.close()
            except Exception:
                pass
        try:
            self.sock_de_recherche.close()
        except Exception:
            pass
        self._stop_mon = True

# -----------------------
# FIN de ports.py
# -----------------------