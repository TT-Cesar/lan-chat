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
    Gestion des sessions, découverte multicast, appropriation de chaîne, et création
    de sessions directes via les informations publiées dans `infos_sup` (IP:4 octets + PORT:2 octets).
    - Filtre les annonces multicast avec CRC valide uniquement.
    - Stocke pour chaque entrée de contenu_chaines un dictionnaire:
        { 'payload': bytes, 'ip': str, 'port': int, 'parsed': dict, 'last_seen': float }
    - Evite les sessions dupliquées en comparant la cle_publique si disponible.
    - Heuristique IP locale : priorise 192.168.x.x, puis 10.x.x.x, puis 172.16-31.x.x, sinon fallback.
    """

    # Constantes attendues (doivent exister dans le module global)
    # - adresses_multicast  (liste)
    # - MULTICAST_PORT
    # - MULTICAST_MSG_SIZE
    # - NOMS_SIZE, PRENOMS_SIZE, TAILLE_CLE_SIZE, CLE_PUB_MAX, INFOS_SUP_SIZE, CRC_SIZE
    # - SESSION_REQUEST, SESSION_ACK
    # - ports_decoutes
    # - paquets (module fourni)
    # - Appareil, Utilisateur, Session (classes définies dans le même module)

    def __init__(self, ip: Optional[str] = None, multicast_active: bool = True):
        # Choix de l'IP local selon heuristique D si non fourni
        self.ip = ip if ip is not None else self._choose_local_ip()
        self.sessions: List[Session] = []
        # Chaque élément de contenu_chaines est soit None soit dict {'payload', 'ip', 'port', 'parsed', 'last_seen'}
        self.contenu_chaines: List[Optional[dict]] = [None] * len(adresses_multicast)
        self.chaine_multicast: Optional[str] = None
        self.code_connexion: Optional[str] = None

        # Socket de recherche multicast : on bind sur 0.0.0.0 pour compat Windows/Linux
        self.sock_de_recherche = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_de_recherche.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # En Windows, bind sur ('', port) ou ('0.0.0.0', port) ; on essaie la liste ports_decoutes
        bound = False
        for p in ports_decoutes:
            try:
                self.sock_de_recherche.bind(('0.0.0.0', p))
                bound = True
                break
            except OSError:
                continue
        if not bound:
            raise OSError("Aucun port d'écoute disponible parmi ports_decoutes")

        # Tenter d'adhérer aux groupes multicast (peut échouer selon l'OS)
        try:
            for adresse in adresses_multicast:
                mreq = socket.inet_aton(adresse) + socket.inet_aton(self.ip)
                self.sock_de_recherche.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception:
            # Si l'ajout massif échoue, on poursuit quand même l'écoute sur la socket.
            pass

        # Threads de monitoring / incoming
        self._stop_mon = False
        if multicast_active:
            self._monitor_thread = threading.Thread(target=self.actualiser_contenu_chaines, daemon=True)
            self._monitor_thread.start()

        self._incoming_thread = threading.Thread(target=self.ecouter_demandes_session, daemon=True)
        self._incoming_thread.start()

    # ---------------------------
    # Heuristique D : choisir IP locale
    # ---------------------------
    def _choose_local_ip(self) -> str:
        """
        Heuristique D :
          - priorise adresses 192.168.x.x
          - sinon 10.x.x.x
          - sinon 172.16–172.31.x.x
          - sinon tente la méthode connect(("8.8.8.8",80))
          - sinon '127.0.0.1' comme fallback
        """
        candidates = []
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
                for a in addrs:
                    ip = a.get('addr')
                    if ip and not ip.startswith('127.'):
                        candidates.append(ip)
        except Exception:
            # netifaces non disponible : essayer connect hack
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                if ip:
                    candidates.append(ip)
            except Exception:
                pass

        # Priorités
        for ip in candidates:
            if ip.startswith("192.168."):
                return ip
        for ip in candidates:
            if ip.startswith("10."):
                return ip
        for ip in candidates:
            parts = ip.split('.')
            if len(parts) == 4:
                first = int(parts[0])
                second = int(parts[1])
                if first == 172 and 16 <= second <= 31:
                    return ip
        # fallback
        return candidates[0] if candidates else "127.0.0.1"

    # ---------------------------
    # Parsing / validation des paquets multicast
    # ---------------------------
    def _parse_multicast_payload(self, payload: bytes) -> Optional[dict]:
        """
        Parse et valide un payload de 1470 octets.
        Vérifie CRC et renvoie un dict parsed :
          {'noms','prenoms','taille_cle','cle_pub','infos_sup'}
        Retourne None si invalide.
        """
        # Vérification de taille brute
        if not payload or len(payload) != MULTICAST_MSG_SIZE:
            return None
        try:
            # séparer le pack et le CRC final
            pack = payload[:-CRC_SIZE]  # tout sauf CRC
            crc_recv = payload[-CRC_SIZE:]
            import binascii as _b
            crc_calc = _b.crc32(pack).to_bytes(4, 'big')
            if crc_calc != crc_recv:
                # CRC invalide : rejeter
                return None
            i = 0
            noms = pack[i:i+NOMS_SIZE].rstrip(b'\x00'); i += NOMS_SIZE
            prenoms = pack[i:i+PRENOMS_SIZE].rstrip(b'\x00'); i += PRENOMS_SIZE
            taille_cle = int.from_bytes(pack[i:i+TAILLE_CLE_SIZE], 'big'); i += TAILLE_CLE_SIZE
            cle_pub = None
            if taille_cle > 0:
                cle_pub = pack[i:i+CLE_PUB_MAX][:taille_cle]
            i += CLE_PUB_MAX
            infos_sup = pack[i:i+INFOS_SUP_SIZE]; i += INFOS_SUP_SIZE
            return {
                'noms': noms.decode(errors='ignore') if noms else "",
                'prenoms': prenoms.decode(errors='ignore') if prenoms else "",
                'taille_cle': taille_cle,
                'cle_pub': cle_pub,
                'infos_sup': infos_sup
            }
        except Exception:
            return None

    # ---------------------------
    # actualiser_contenu_chaines : thread de surveillance multicast
    # ---------------------------
    def actualiser_contenu_chaines(self):
        """
        Boucle d'écoute sur self.sock_de_recherche. Stocke uniquement les annonces
        ayant une CRC valide (via _parse_multicast_payload). Pour chaque réception,
        stocke payload + ip_source + port_source + parsed + last_seen.
        """
        self.sock_de_recherche.settimeout(0.1)
        while not self._stop_mon:
            try:
                data, (ip_src, port_src) = self.sock_de_recherche.recvfrom(4096)
                parsed = self._parse_multicast_payload(data)
                if parsed is None:
                    # CRC invalide ou format incorrect : ignorer
                    continue
                # infos_sup contient au moins 6 octets : IP(4) + PORT(2)
                infos = parsed.get('infos_sup', b'\x00' * INFOS_SUP_SIZE)
                try:
                    ip_bytes = infos[0:4]
                    port_bytes = infos[4:6]
                    ip_from_infos = socket.inet_ntoa(ip_bytes)
                    port_from_infos = int.from_bytes(port_bytes, 'big')
                except Exception:
                    # Si infos_sup mal formée, on utilise ip_src/port_src comme fallback
                    ip_from_infos = ip_src
                    port_from_infos = port_src

                # trouver un slot libre ou mise à jour d'un existant (match par cle_pub si possible)
                now = time.time()
                stored = False
                # si le message contient une clé publique connue, essayer de mettre à jour sa position existante
                cle_pub = parsed.get('cle_pub')
                if cle_pub:
                    for i, entry in enumerate(self.contenu_chaines):
                        if entry and entry.get('parsed') and entry['parsed'].get('cle_pub') == cle_pub:
                            # mise à jour de l'entrée
                            self.contenu_chaines[i] = {
                                'payload': data,
                                'ip': ip_from_infos,
                                'port': port_from_infos,
                                'parsed': parsed,
                                'last_seen': now
                            }
                            stored = True
                            break

                if not stored:
                    # stocker dans le premier None ou écraser la plus vieille
                    for i in range(len(self.contenu_chaines)):
                        if self.contenu_chaines[i] is None:
                            self.contenu_chaines[i] = {
                                'payload': data,
                                'ip': ip_from_infos,
                                'port': port_from_infos,
                                'parsed': parsed,
                                'last_seen': now
                            }
                            stored = True
                            break
                    if not stored:
                        # écraser la plus vieille
                        oldest = 0
                        oldest_time = self.contenu_chaines[0]['last_seen'] if self.contenu_chaines[0] else now
                        for j in range(1, len(self.contenu_chaines)):
                            if self.contenu_chaines[j] and self.contenu_chaines[j]['last_seen'] < oldest_time:
                                oldest = j
                                oldest_time = self.contenu_chaines[j]['last_seen']
                        self.contenu_chaines[oldest] = {
                            'payload': data,
                            'ip': ip_from_infos,
                            'port': port_from_infos,
                            'parsed': parsed,
                            'last_seen': now
                        }
            except socket.timeout:
                continue
            except Exception:
                # ignorer erreurs ponctuelles
                continue

    # ---------------------------
    # Construire payload multicast (utilisé si on publie notre propre annonce)
    # ---------------------------
    def _build_multicast_payload(self, noms: bytes = None, prenoms: bytes = None,
                                 cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None) -> bytes:
        """
        Construire le message 1470 octets :
        [NOMS:200][PRENOMS:200][TAILLE_CLE:2][CLE_PUB:1024][INFOS_SUP:40][CRC:4]
        infos_sup[0:4]=IP (self.ip), [4:6]=port_reception
        """
        noms_b = (noms or b"")[:NOMS_SIZE].ljust(NOMS_SIZE, b'\x00')
        prenoms_b = (prenoms or b"")[:PRENOMS_SIZE].ljust(PRENOMS_SIZE, b'\x00')
        if cle_pub:
            taille = len(cle_pub)
            if taille > CLE_PUB_MAX:
                cle_pub = cle_pub[:CLE_PUB_MAX]
                taille = CLE_PUB_MAX
            taille_field = taille.to_bytes(TAILLE_CLE_SIZE, 'big')
            cle_field = cle_pub.ljust(CLE_PUB_MAX, b'\x00')
        else:
            taille_field = (0).to_bytes(TAILLE_CLE_SIZE, 'big')
            cle_field = b'\x00' * CLE_PUB_MAX

        # infos_sup : IP (4) + PORT (2) + padding 34
        try:
            ip_bytes = socket.inet_aton(self.ip)
        except Exception:
            ip_bytes = b'\x00\x00\x00\x00'
        port_field = (port_reception if port_reception is not None else 0).to_bytes(2, 'big')
        infos = ip_bytes + port_field + (b'\x00' * (INFOS_SUP_SIZE - 6))

        pack = noms_b + prenoms_b + taille_field + cle_field + infos
        # CRC final
        try:
            import binascii as _b
            crc4 = _b.crc32(pack).to_bytes(4, 'big')
        except Exception:
            crc4 = b'\x00' * 4
        return pack + crc4

    # ---------------------------
    # Publier une annonce unique sur une adresse multicast donnée
    # ---------------------------
    def publier_message_sur_chaine_onadresse(self, adresse: str, noms: bytes = None, prenoms: bytes = None,
                                             cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None):
        """
        Envoie une seule annonce sur `adresse` en utilisant self._build_multicast_payload.
        """
        payload = self._build_multicast_payload(noms, prenoms, cle_pub, port_reception)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            ttl = 1
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            except Exception:
                pass
            sock.sendto(payload, (adresse, MULTICAST_PORT))
        finally:
            try:
                sock.close()
            except Exception:
                pass

    # ---------------------------
    # Trouver/approprier une chaîne multicast libre (procédure d'appropriation)
    # ---------------------------
    def trouver_chaine_multicast(self, noms: bytes = None, prenoms: bytes = None,
                                 cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None,
                                 listen_interval: float = 0.12, attempts: int = 2, backoff_max: float = 0.08) -> Optional[str]:
        """
        Tente d'approprier une chaîne multicast libre et démarre un broadcast périodique si réussi.
        Renvoie l'adresse multicast choisie ou None.
        """
        for adresse in adresses_multicast:
            # test silence rapide
            if not self._is_chain_quiet(adresse, listen_interval):
                continue
            # tentative d'appropriation
            for attempt in range(attempts):
                # envoyer annonce unique
                self.publier_message_sur_chaine_onadresse(adresse, noms, prenoms, cle_pub, port_reception)
                # courte écoute pour détecter collision
                time.sleep(listen_interval / 2.0)
                if self._is_chain_quiet(adresse, listen_interval / 2.0):
                    # adopt
                    self.chaine_multicast = adresse
                    # lancer broadcast permanent
                    t = threading.Thread(target=self._broadcast_loop, args=(adresse, noms, prenoms, cle_pub, port_reception), daemon=True)
                    t.start()
                    return adresse
                else:
                    time.sleep(random.random() * backoff_max)
                    continue
        return None

    def _is_chain_quiet(self, adresse: str, duree: float) -> bool:
        """
        Vérifie si une adresse multicast est silencieuse pendant `duree` secondes.
        Créé un socket temporaire et rejoint le groupe.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(duree)
        try:
            try:
                mreq = socket.inet_aton(adresse) + socket.inet_aton(self.ip)
                s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except Exception:
                pass
            try:
                s.recvfrom(1024)
                return False
            except socket.timeout:
                return True
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _broadcast_loop(self, adresse: str, noms: bytes = None, prenoms: bytes = None,
                        cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None):
        """
        Envoi périodique d'annonces sur la chaîne appropriée.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            except Exception:
                pass
            while self.chaine_multicast == adresse:
                payload = self._build_multicast_payload(noms, prenoms, cle_pub, port_reception)
                try:
                    sock.sendto(payload, (adresse, MULTICAST_PORT))
                except Exception:
                    pass
                time.sleep(ANNOUNCE_INTERVAL)
        finally:
            try:
                sock.close()
            except Exception:
                pass

    # ---------------------------
    # Création de session directe depuis un index de detection multicast
    # ---------------------------
    def creer_session_par_multicast(self, index: int, fdc: Optional[Callable] = None, cle: Optional[bytes] = None,
                                    timeout: float = 0.5, retry: int = 3) -> Session:
        """
        Récupère l'entrée contenu_chaines[index], extrait ip/port (depuis infos_sup),
        vérifie qu'on n'a pas déjà une session avec cette cle_publique (si disponible),
        prépare un socket local (bind '0.0.0.0',0), envoie SESSION_REQUEST, attend SESSION_ACK,
        puis crée la Session et l'ajoute à self.sessions.
        """
        if index < 0 or index >= len(self.contenu_chaines):
            raise IndexError("Index hors plage pour contenu_chaines")
        entry = self.contenu_chaines[index]
        if not entry:
            raise ValueError("Aucune annonce à cet index")
        parsed = entry.get('parsed')
        ip_target = entry.get('ip') or None
        port_target = entry.get('port') or None
        if not ip_target or not port_target:
            # fallback try to read infos_sup raw
            if parsed:
                infos = parsed.get('infos_sup', b'\x00'*INFOS_SUP_SIZE)
                try:
                    ip_target = socket.inet_ntoa(infos[0:4])
                    port_target = int.from_bytes(infos[4:6], 'big')
                except Exception:
                    raise ConnectionError("Impossible de déterminer IP/port du pair depuis l'annonce")
        # éviter duplication : si on a une clé publique pour ce pair, vérifier s'il existe déjà une session
        cle_pub_peer = parsed.get('cle_pub') if parsed else None
        if cle_pub_peer:
            for s in self.sessions:
                try:
                    peer_cle = s.destinataire.ut.cle_publique
                    if peer_cle and peer_cle == cle_pub_peer:
                        raise ConnectionError("Session déjà existante avec ce pair (clé publique identique)")
                except Exception:
                    continue

        # préparer socket local bindé sur 0.0.0.0:0 (compatible Windows)
        sock_local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_local.bind(('0.0.0.0', 0))
        sock_local.settimeout(timeout)
        local_port = sock_local.getsockname()[1]

        # Envoi SESSION_REQUEST + indique le port local où on souhaite recevoir (2-octets)
        request_payload = SESSION_REQUEST + local_port.to_bytes(2, 'big')
        success = False
        for attempt in range(retry):
            try:
                sock_local.sendto(request_payload, (ip_target, port_target))
                data, _ = sock_local.recvfrom(64)
                # accepter uniquement un ACK strict
                if data == SESSION_ACK:
                    success = True
                    break
            except socket.timeout:
                continue
            except Exception:
                continue

        if not success:
            sock_local.close()
            raise ConnectionError("Pas de réponse à SESSION_REQUEST depuis le pair")

        # réussi -> créer utilisateur temporaire et Session
        utilisateur_temp = Utilisateur([parsed.get('noms') or "Inconnu"], [parsed.get('prenoms') or "Inconnu"],
                                       cle_privee=None, cle_publique=cle_pub_peer)
        appareil = Appareil(ip_target, port_target, utilisateur_temp)
        session = Session(sock_local, appareil, fdc, cle)
        # ajouter session à la liste
        self.sessions.append(session)
        return session

    # ---------------------------
    # Méthode utilitaire : generer code connexion
    # ---------------------------
    def generer_code_connexion(self, port_libre: int) -> str:
        return encode_connexion_code(self.ip, port_libre)

    # ---------------------------
    # Liste des sessions actives
    # ---------------------------
    def liste_sessions_actives(self) -> List[Session]:
        return [s for s in self.sessions if s.session_active]

    # -------------------------------------------------------------------
    # Écoute des demandes de session (P2P) depuis d'autres appareils
    # -------------------------------------------------------------------
    def ecouter_demandes_session(self):
        """
        Écoute en continu sur sock_de_recherche des demandes de session
        envoyées par d'autres appareils.

        FORMAT D'UNE DEMANDE SESSION_REQUEST :
            [0]    = octet SESSION_REQUEST
            [1:3]  = port_local_du_demandeur (2 octets big-endian)

        ACTION :
            - envoyer immédiatement SESSION_ACK au port fourni
            - créer automatiquement une Session côté local si nécessaire
        """
        while not self._stop_mon:
            try:
                data, (ip_src, port_src) = self.sock_de_recherche.recvfrom(64)
            except Exception:
                time.sleep(0.05)
                continue

            if not data:
                continue

            # Vérifier qu'il s'agit d'une demande SESSION_REQUEST
            if data[0:1] != SESSION_REQUEST:
                continue

            # Lire le port sur lequel le demandeur souhaite recevoir la réponse
            try:
                port_reception_demandeur = int.from_bytes(data[1:3], "big")
            except:
                continue

            # 1) Répondre par SESSION_ACK
            try:
                self.sock_de_recherche.sendto(SESSION_ACK, (ip_src, port_reception_demandeur))
            except:
                continue

            # 2) Créer la Session côté local (Alice)
            # Vérifier si déjà existante (clé publique ou IP/Port)
            # Cela dépend de ta logique d'unicité, mais on peut mettre:
            existe = False
            for s in self.sessions:
                if s.destinataire.ip == ip_src:
                    existe = True
                    break

            if existe:
                continue  # session déjà existante

            # Sinon créer la session passive
            try:
                # Préparation utilisateur temporaire (peut évoluer après authentification)
                ut = Utilisateur(
                    noms=["Inconnu"],
                    prenoms=["Inconnu"],
                    cle_publique=None,
                    cle_privee=None
                )

                # L'appareil distant
                appareil = Appareil(ip_src, port_src, ut)

                # Socket local pour communication
                sock_local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock_local.bind(("0.0.0.0", 0))

                # Création Session
                session = Session(sock_local, appareil, None, None)
                session.session_active = True

                self.sessions.append(session)

            except Exception:
                continue
    # ---------------------------
    # Fermeture et cleanup
    # ---------------------------
    def close_all(self):
        self._stop_mon = True
        try:
            self.sock_de_recherche.close()
        except Exception:
            pass
        for s in list(self.sessions):
            try:
                s.close()
            except Exception:
                pass
        self.sessions.clear()
# -----------------------
# FIN de ports.py
# -----------------------