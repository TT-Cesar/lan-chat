# ports.py
"""
Gestion des ports, découverte multicast, création de sessions et
authentification optionnelle (callbacks assignés par Chats).
"""

import socket
import threading
import time
import secrets
import random
from typing import List, Optional, Callable, Tuple

import paquets

# -------------------------------------------------------------------
# Constantes et configuration
# -------------------------------------------------------------------

BASE64_CUSTOM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?"

# Plage multicast privée (301 adresses)
base = "239.192.{}"
adresses_multicast: List[str] = []
for troisieme in range(1, 3):
    for quatrieme in range(1, 256):
        if len(adresses_multicast) >= 301:
            break
        adresses_multicast.append(base.format(f"{troisieme}.{quatrieme}"))

# Ports d'écoute "préférés" 
ports_decoutes = [
    54321, 58732, 61248, 49876, 52413,
    59987, 63254, 50789, 57801, 64523
]

# Multicast par défaut
MULTICAST_GROUP_DEFAULT = "239.192.1.1"
MULTICAST_PORT = 54321

# Durées
MULTICAST_LISTEN_INTERVAL = 0.12
BACKOFF_MAX = 0.08
APPROPRIATION_ATTEMPTS = 2
ANNOUNCE_INTERVAL = 0.6
SOCKET_RECV_BUFFER = 2048

# Paquets de handshake
SESSION_REQUEST = b"PORTS_SESSION_REQ"
SESSION_ACK = b"PORTS_SESSION_ACK"

# Multicast message format sizes
NOMS_SIZE = 200
PRENOMS_SIZE = 200
TAILLE_CLE_SIZE = 2
CLE_PUB_MAX = 1024
INFOS_SUP_SIZE = 40
CRC_SIZE = 4
MULTICAST_MSG_SIZE = NOMS_SIZE + PRENOMS_SIZE + TAILLE_CLE_SIZE + CLE_PUB_MAX + INFOS_SUP_SIZE + CRC_SIZE

# -------------------------------------------------------------------

def encode_connexion_code(ip: str, port: int, alphabet: str = BASE64_CUSTOM) -> str:
    """Encode IP + port en code de 8 caractères."""
    if ip == "localhost":
        octets = [127, 0, 0, 1]
    else:
        octets = [int(x) for x in ip.split(".")]
    bits = "".join(format(b, "08b") for b in octets) + format(port, "016b")
    blocs = [bits[i * 6:(i + 1) * 6] for i in range(8)]
    return "".join(alphabet[int(b, 2)] for b in blocs)

def decode_connexion_code(code: str, alphabet: str = BASE64_CUSTOM) -> Tuple[str, int]:
    """Décode un code de 8 caractères en (ip, port)."""
    if len(code) != 8:
        raise ValueError("Le code doit faire 8 caractères.")
    bits = "".join(format(alphabet.index(c), "06b") for c in code)
    A = int(bits[0:8], 2)
    B = int(bits[8:16], 2)
    C = int(bits[16:24], 2)
    D = int(bits[24:32], 2)
    port = int(bits[32:48], 2)
    return f"{A}.{B}.{C}.{D}", port

class Utilisateur:
    def __init__(self, noms: List[str], prenoms: List[str],
                 cle_privee: Optional[bytes] = None,
                 cle_publique: Optional[bytes] = None):
        self.noms = noms
        self.prenoms = prenoms
        self.cle_privee = cle_privee
        self.cle_publique = cle_publique
        self.authentique = False

    def est_local(self) -> bool:
        return self.cle_privee is not None

    def set_cle_publique(self, cle_pub: bytes):
        self.cle_publique = cle_pub

    def is_authenticated(self) -> bool:
        return self.authentique

class Appareil:
    def __init__(self, ip: str, port: int, ut: Utilisateur):
        self.ip = ip
        self.port = port
        self.ut = ut
        self.sock_recep = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class Session:
    def __init__(self, sock_local: socket.socket, destinataire: Appareil,
                 fdc: Optional[Callable] = None, cle: Optional[bytes] = None):
        self.cet_appareil = sock_local
        self.destinataire = destinataire
        self.fdc = fdc
        self.cle = cle

        self.octets_envoyes: List[bytes] = []
        self.octets_recus: List[bytes] = []

        from queue import Queue
        self.octets_a_envoyer = Queue()
        self.octets_a_recevoir = Queue()

        self.session_active = False
        self.authentique = False

        self.demander_preuve: Optional[Callable] = None
        self.fournir_preuve: Optional[Callable] = None
        self.confirmer_preuve: Optional[Callable] = None

        self._thread_envoi = None
        self._stop_threads = False

    def envoyer_octets(self, octets: bytes, tdc: bytes = b'\x00', infos_sup: bytes = b'\x00\x00\x00\x00'):
        """Envoie des octets via paquets.charger_octets."""
        paq_list = paquets.charger_octets(octets, self.fdc if self.fdc is not None else paquets.NotImplemented,
                                          self.cle if self.cle is not None else b'', tdc, infos_sup)
        for p in paq_list:
            self.cet_appareil.sendto(p, (self.destinataire.ip, self.destinataire.port))
        self.octets_envoyes.append(octets)

    def recevoir_octets(self, paquets_list: List[bytes]):
        """Reconstitue les octets via paquets.decharger_octets."""
        octets = paquets.decharger_octets(paquets_list, paquets.NotImplemented, b'')
        self.octets_recus.append(octets)
        return octets

    def thread_envoi(self):
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

    def _echange_cle(self):
        """Échange Diffie-Hellman minimaliste."""
        a = secrets.randbelow(paquets.__dict__.get('p', 0xFFFFFFFF)) if hasattr(paquets, 'p') else secrets.randbelow(1 << 256)
        A = pow(paquets.__dict__.get('g', 2) if hasattr(paquets, 'g') else 2, a, paquets.__dict__.get('p', (1 << 2048) - 1))
        self.cet_appareil.sendto(A.to_bytes((A.bit_length() + 7) // 8, 'big'),
                                 (self.destinataire.ip, self.destinataire.port))
        data, _ = self.cet_appareil.recvfrom(4096)
        B = int.from_bytes(data, 'big')
        K = pow(B, a, paquets.__dict__.get('p', (1 << 2048) - 1))
        return K.to_bytes((K.bit_length() + 7) // 8, 'big')

    def creer_session(self, initiateur: bool = True, timeout: float = 1.0):
        """Crée/initialise la session."""
        if self.fdc is not None:
            try:
                cle_secrete = self._echange_cle()
                self.cle = cle_secrete
            except Exception:
                self.cle = None

        try:
            if self.demander_preuve is not None:
                result = self.demander_preuve(self)
                self.authentique = bool(result)
            else:
                self.authentique = False
        except Exception:
            self.authentique = False

        self.session_active = True
        self.thread_envoi()

    def get_historique(self) -> dict:
        return {
            'envoyes': list(self.octets_envoyes),
            'recus': list(self.octets_recus),
            'authentique': bool(self.authentique)
        }

    def close(self):
        self._stop_threads = True
        self.session_active = False

class Chats:
    def __init__(self, ip: Optional[str] = None, multicast_active: bool = True):
        self.ip = ip if ip is not None else self._choose_local_ip()
        self.sessions: List[Session] = []
        self.contenu_chaines: List[Optional[dict]] = [None] * len(adresses_multicast)
        self.chaine_multicast: Optional[str] = None
        self.code_connexion: Optional[str] = None
        
        # Nouveau: Socket P2P dédiée pour les sessions
        self.sock_p2p = self._creer_socket_p2p()
        self.port_p2p = self.sock_p2p.getsockname()[1] if self.sock_p2p else None

        # Socket de recherche multicast
        self.sock_de_recherche = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_de_recherche.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
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

        # Adhésion aux groupes multicast
        try:
            for adresse in adresses_multicast:
                mreq = socket.inet_aton(adresse) + socket.inet_aton(self.ip)
                self.sock_de_recherche.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception:
            pass

        # Démarrer la diffusion multicast automatiquement
        if multicast_active:
            self.trouver_chaine_multicast()

        self._stop_mon = False
        if multicast_active:
            self._monitor_thread = threading.Thread(target=self.actualiser_contenu_chaines, daemon=True)
            self._monitor_thread.start()

        self._incoming_thread = threading.Thread(target=self.ecouter_demandes_session, daemon=True)
        self._incoming_thread.start()

    def _creer_socket_p2p(self) -> socket.socket:
        """Crée une socket P2P dédiée sur un port libre."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 0))  # Port aléatoire libre
        return sock

    def _choose_local_ip(self) -> str:
        """
        Heuristique pour choisir l'IP locale.
        METHODE AMÉLIORÉE : Tente d'abord de déterminer l'interface par défaut (route vers internet),
        puis fallback sur l'itération des interfaces si hors ligne.
        """
        # 1. Méthode prioritaire : Demander à l'OS quelle IP est utilisée pour sortir (Google DNS)
        # Cette méthode ne connecte pas vraiment (UDP), mais consulte la table de routage.
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

        # 2. Méthode de secours (Fallback) : Si pas d'internet/route, on liste tout
        candidates = []
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
                for a in addrs:
                    ip = a.get('addr')
                    if ip and not ip.startswith('127.'):
                        candidates.append(ip)
        except ImportError:
            # Si netifaces n'est pas installé, on ignore
            pass
        except Exception:
            pass

        # Fallback supplémentaire si netifaces échoue ou n'est pas là
        if not candidates:
            try:
                ip = socket.gethostbyname(socket.gethostname())
                if ip and not ip.startswith("127."):
                    candidates.append(ip)
            except Exception:
                pass

        # Logique de tri existante
        for ip in candidates:
            if ip.startswith("192.168."):
                return ip
        for ip in candidates:
            if ip.startswith("10."):
                return ip
        for ip in candidates:
            parts = ip.split('.')
            if len(parts) == 4:
                try:
                    first = int(parts[0])
                    second = int(parts[1])
                    if first == 172 and 16 <= second <= 31:
                        return ip
                except ValueError:
                    continue
                    
        return candidates[0] if candidates else "127.0.0.1"

    def _parse_multicast_payload(self, payload: bytes) -> Optional[dict]:
        """Parse et valide un payload multicast."""
        if not payload or len(payload) != MULTICAST_MSG_SIZE:
            return None
        try:
            pack = payload[:-CRC_SIZE]
            crc_recv = payload[-CRC_SIZE:]
            import binascii as _b
            crc_calc = _b.crc32(pack).to_bytes(4, 'big')
            if crc_calc != crc_recv:
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

    def actualiser_contenu_chaines(self):
        """Boucle d'écoute des annonces multicast."""
        self.sock_de_recherche.settimeout(0.1)
        while not self._stop_mon:
            try:
                data, (ip_src, port_src) = self.sock_de_recherche.recvfrom(4096)
                parsed = self._parse_multicast_payload(data)
                if parsed is None:
                    continue
                    
                infos = parsed.get('infos_sup', b'\x00' * INFOS_SUP_SIZE)
                try:
                    ip_bytes = infos[0:4]
                    port_bytes = infos[4:6]
                    ip_from_infos = socket.inet_ntoa(ip_bytes)
                    port_from_infos = int.from_bytes(port_bytes, 'big')
                except Exception:
                    ip_from_infos = ip_src
                    port_from_infos = port_src

                # NOUVEAU: Détection des doublons par IP:port
                deja_present = False
                for i, entry in enumerate(self.contenu_chaines):
                    if entry and entry.get('ip') == ip_from_infos and entry.get('port') == port_from_infos:
                        # Mise à jour de l'entrée existante
                        self.contenu_chaines[i] = {
                            'payload': data,
                            'ip': ip_from_infos,
                            'port': port_from_infos,
                            'parsed': parsed,
                            'last_seen': time.time()
                        }
                        deja_present = True
                        break

                if not deja_present:
                    # Stocker dans le premier slot libre
                    for i in range(len(self.contenu_chaines)):
                        if self.contenu_chaines[i] is None:
                            self.contenu_chaines[i] = {
                                'payload': data,
                                'ip': ip_from_infos,
                                'port': port_from_infos,
                                'parsed': parsed,
                                'last_seen': time.time()
                            }
                            break
                    else:
                        # Écraser la plus vieille entrée
                        oldest_index = min(range(len(self.contenu_chaines)), 
                                         key=lambda i: self.contenu_chaines[i]['last_seen'] if self.contenu_chaines[i] else float('inf'))
                        self.contenu_chaines[oldest_index] = {
                            'payload': data,
                            'ip': ip_from_infos,
                            'port': port_from_infos,
                            'parsed': parsed,
                            'last_seen': time.time()
                        }
            except socket.timeout:
                continue
            except Exception:
                continue

    def _build_multicast_payload(self, noms: bytes = None, prenoms: bytes = None,
                                 cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None) -> bytes:
        """Construit le message multicast avec le port P2P actuel."""
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

        # NOUVEAU: Utiliser le port P2P dédié dans infos_sup
        try:
            ip_bytes = socket.inet_aton(self.ip)
        except Exception:
            ip_bytes = b'\x00\x00\x00\x00'
        port_field = (self.port_p2p if port_reception is None else port_reception).to_bytes(2, 'big')
        infos = ip_bytes + port_field + (b'\x00' * (INFOS_SUP_SIZE - 6))

        pack = noms_b + prenoms_b + taille_field + cle_field + infos
        try:
            import binascii as _b
            crc4 = _b.crc32(pack).to_bytes(4, 'big')
        except Exception:
            crc4 = b'\x00' * 4
        return pack + crc4

    def publier_message_sur_chaine_onadresse(self, adresse: str, noms: bytes = None, prenoms: bytes = None,
                                             cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None):
        """Envoie une annonce sur une adresse multicast."""
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

    def trouver_chaine_multicast(self, noms: bytes = None, prenoms: bytes = None,
                                 cle_pub: Optional[bytes] = None, port_reception: Optional[int] = None) -> Optional[str]:
        """Tente d'approprier une chaîne multicast et démarre la diffusion."""
        for adresse in adresses_multicast:
            if not self._is_chain_quiet(adresse, MULTICAST_LISTEN_INTERVAL):
                continue
            for attempt in range(APPROPRIATION_ATTEMPTS):
                self.publier_message_sur_chaine_onadresse(adresse, noms, prenoms, cle_pub, port_reception)
                time.sleep(MULTICAST_LISTEN_INTERVAL / 2.0)
                if self._is_chain_quiet(adresse, MULTICAST_LISTEN_INTERVAL / 2.0):
                    self.chaine_multicast = adresse
                    # NOUVEAU: Démarrer la diffusion périodique avec les bonnes infos
                    t = threading.Thread(target=self._broadcast_loop, args=(adresse,), daemon=True)
                    t.start()
                    return adresse
                else:
                    time.sleep(random.random() * BACKOFF_MAX)
        return None

    def _is_chain_quiet(self, adresse: str, duree: float) -> bool:
        """Vérifie si une chaîne multicast est silencieuse."""
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

    def _broadcast_loop(self, adresse: str):
        """Diffusion périodique d'annonces sur la chaîne appropriée."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            try:
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            except Exception:
                pass
            while self.chaine_multicast == adresse:
                # NOUVEAU: Utiliser les informations de l'utilisateur courant
                payload = self._build_multicast_payload(
                    noms=b"Host",  # À remplacer par CURRENT_USER
                    prenoms=b"Test",
                    cle_pub=None,
                    port_reception=self.port_p2p
                )
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

    def creer_session_par_multicast(self, index: int, fdc: Optional[Callable] = None, cle: Optional[bytes] = None,
                                    timeout: float = 0.5, retry: int = 3) -> Session:
        """Crée une session avec un appareil détecté via multicast."""
        if index < 0 or index >= len(self.contenu_chaines):
            raise IndexError("Index hors plage pour contenu_chaines")
        entry = self.contenu_chaines[index]
        if not entry:
            raise ValueError("Aucune annonce à cet index")
            
        parsed = entry.get('parsed')
        ip_target = entry.get('ip')
        port_target = entry.get('port')
        
        if not ip_target or not port_target:
            if parsed:
                infos = parsed.get('infos_sup', b'\x00'*INFOS_SUP_SIZE)
                try:
                    ip_target = socket.inet_ntoa(infos[0:4])
                    port_target = int.from_bytes(infos[4:6], 'big')
                except Exception:
                    raise ConnectionError("Impossible de déterminer IP/port du pair")

        # NOUVEAU: Détection des doublons par IP:port
        for s in self.sessions:
            if (s.destinataire.ip == ip_target and 
                s.destinataire.port == port_target and 
                s.session_active):
                raise ConnectionError("Session déjà existante avec ce pair")

        # Utiliser la socket P2P dédiée pour la session
        sock_local = self.sock_p2p
        success = False
        
        for attempt in range(retry):
            try:
                # NOUVEAU: Envoyer la demande sur le port P2P de la cible
                sock_local.sendto(SESSION_REQUEST, (ip_target, port_target))
                sock_local.settimeout(timeout)
                data, addr = sock_local.recvfrom(64)
                if data == SESSION_ACK:
                    success = True
                    break
            except socket.timeout:
                continue
            except Exception:
                continue

        if not success:
            raise ConnectionError("Pas de réponse à SESSION_REQUEST depuis le pair")

        utilisateur_temp = Utilisateur([parsed.get('noms') or "Inconnu"], [parsed.get('prenoms') or "Inconnu"],
                                       cle_privee=None, cle_publique=parsed.get('cle_pub'))
        appareil = Appareil(ip_target, port_target, utilisateur_temp)
        session = Session(sock_local, appareil, fdc, cle)
        
        # NOUVEAU: Démarrer la session automatiquement
        session.creer_session(initiateur=True)
        self.sessions.append(session)
        return session

    def generer_code_connexion(self) -> str:
        """Génère un code de connexion avec le port P2P actuel."""
        if not self.port_p2p:
            raise ValueError("Aucun port P2P disponible")
        return encode_connexion_code(self.ip, self.port_p2p)

    def liste_sessions_actives(self) -> List[Session]:
        return [s for s in self.sessions if s.session_active]

    def ecouter_demandes_session(self):
        """Écoute les demandes de session sur la socket P2P."""
        while not self._stop_mon:
            try:
                data, (ip_src, port_src) = self.sock_p2p.recvfrom(64)
            except Exception:
                time.sleep(0.05)
                continue

            if not data or data != SESSION_REQUEST:
                continue

            # Répondre par SESSION_ACK
            try:
                self.sock_p2p.sendto(SESSION_ACK, (ip_src, port_src))
            except:
                continue

            # Vérifier si session existe déjà
            for s in self.sessions:
                if s.destinataire.ip == ip_src and s.destinataire.port == port_src:
                    continue

            # Créer une nouvelle session passive
            try:
                ut = Utilisateur(["Inconnu"], ["Inconnu"], cle_publique=None, cle_privee=None)
                appareil = Appareil(ip_src, port_src, ut)
                session = Session(self.sock_p2p, appareil, None, None)
                session.session_active = True
                self.sessions.append(session)
            except Exception:
                continue

    def close_all(self):
        self._stop_mon = True
        try:
            self.sock_de_recherche.close()
        except Exception:
            pass
        try:
            self.sock_p2p.close()
        except Exception:
            pass
        for s in list(self.sessions):
            try:
                s.close()
            except Exception:
                pass
        self.sessions.clear()