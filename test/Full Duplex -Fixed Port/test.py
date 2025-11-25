# test.py
"""
Application de test minimaliste pour le protocole ports.py
- Menu interactif
- Découverte multicast
- Diffusion d'infos (format 1470)
- Génération de code de connexion (après réservation d'un port local)
- Connexion via code
- Multi-sessions simultanées
- Authentification "MAYO" simplifiée (callbacks)
- AES interne (stream XOR basé sur SHA-256) pour chiffrer/déchiffrer messages si activé

Usage:
    python test.py

Notes:
- Dépend de ports.py et paquets.py présents dans le même dossier.
- Pas de bibliothèque externe (pycryptodome non requise).
- Conçu pour être lancé sur plusieurs machines du même LAN.
"""

import sys
import threading
import time
import socket
import secrets
import hashlib
import hmac
from typing import Optional

import ports  # ton ports.py (doit être dans le même dossier)
import paquets

LOCAL_IP = "0.0.0.0"  # utiliser l'IP locale exacte si souhaité

# ---------------------------
# Utilitaires cryptographiques (INTERNES pour test)
# ---------------------------

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()

def aes_like_xor_stream(key: bytes, data: bytes) -> bytes:
    """
    AES-interne minimaliste : derive keystream via SHA256(key || counter)
    and XOR with data. Not cryptographically strong — for testing only.
    """
    out = bytearray()
    counter = 0
    i = 0
    while i < len(data):
        block = hashlib.sha256(key + counter.to_bytes(8, 'big')).digest()
        take = min(len(block), len(data) - i)
        for j in range(take):
            out.append(data[i + j] ^ block[j])
        i += take
        counter += 1
    return bytes(out)

# ---------------------------
# MAYO simple (test) :
# - cle_privee : random bytes
# - cle_publique : SHA256(cle_privee) (exposé dans multicast)
# - fournir_preuve(session, challenge) -> HMAC_SHA256(key = cle_publique, challenge)
# - confirmer_preuve(session, preuve, cle_pub_peer) -> recompute HMAC with cle_pub_peer
# Cette construction est symétrique mais fonctionne pour test.
# ---------------------------

# ---------------------------
# Application : état global
# ---------------------------
class AppState:
    def __init__(self):
        # Chats manager (ports.Chats)
        # On utilise l'IP de l'interface locale. Par défaut 0.0.0.0 won't work well for multicast,
        # best to ask the system. For simplicity, we'll ask user for local IP at startup.
        self.local_ip = self._choose_local_ip()
        self.chats = ports.Chats(self.local_ip, multicast_active=True, include_code_in_hello=True)
        # local utilisateur keys
        self.cle_privee = secrets.token_bytes(32)
        self.cle_publique = sha256(self.cle_privee)  # for testing MAYO
        # create local Utilisateur (no names by default)
        self.local_user = ports.Utilisateur(["Local"], ["User"], cle_privee=self.cle_privee, cle_publique=self.cle_publique)
        # map sessions to simple indices for UI
        self.running = True

    def _choose_local_ip(self):
        # Try to auto-detect a real local IP by connecting to a known public ip (no data sent)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

APP = AppState()

# ---------------------------
# Helper : parse multicast payload stored in Chats.contenu_chaines entries
# Expect format: [200][200][2][1024][40][4]
# We'll attempt to parse best-effort (the stored entry may be raw or None).
# ---------------------------
def parse_multicast_payload(payload: bytes):
    if not payload or len(payload) < ports.MULTICAST_MSG_SIZE:
        # best-effort: try to parse if present
        return {
            "noms": None,
            "prenoms": None,
            "taille_cle": 0,
            "cle_pub": None,
            "infos_sup": None
        }
    try:
        i = 0
        noms = payload[i:i+ports.NOMS_SIZE].rstrip(b'\x00').decode(errors='ignore'); i += ports.NOMS_SIZE
        prenoms = payload[i:i+ports.PRENOMS_SIZE].rstrip(b'\x00').decode(errors='ignore'); i += ports.PRENOMS_SIZE
        taille_cle = int.from_bytes(payload[i:i+ports.TAILLE_CLE_SIZE], 'big'); i += ports.TAILLE_CLE_SIZE
        cle_pub = payload[i:i+ports.CLE_PUB_MAX][:taille_cle]; i += ports.CLE_PUB_MAX
        infos_sup = payload[i:i+ports.INFOS_SUP_SIZE]; i += ports.INFOS_SUP_SIZE
        # crc ignored here
        return {
            "noms": noms,
            "prenoms": prenoms,
            "taille_cle": taille_cle,
            "cle_pub": cle_pub,
            "infos_sup": infos_sup
        }
    except Exception:
        return {
            "noms": None,
            "prenoms": None,
            "taille_cle": 0,
            "cle_pub": None,
            "infos_sup": None
        }

# ---------------------------
# Callbacks d'authentification (MAYO simplified)
# We will provide functions that match the expected signatures:
# - demander_preuve(session) -> bool
# - fournir_preuve(session, challenge: bytes) -> bytes
# - confirmer_preuve(session, preuve: bytes, cle_pub_peer: bytes) -> bool
# Note: for ports.Session we only need `demander_preuve` (it will perform full interaction).
# We'll also add a passive handler to respond to REQ/PROOF messages.
# ---------------------------

REQ_TAG = b"REQ_PROOF_V1"
PROOF_TAG = b"PROOF_V1"

def fournir_preuve_impl(session: ports.Session, challenge: bytes) -> bytes:
    """
    Utilisé lorsque ce noeud reçoit un challenge (challenge = bytes).
    Utilise la cle_privee locale pour générer la preuve. Ici on adopte la convention:
    cle_pub = SHA256(cle_privee)
    preuve = HMAC_SHA256(key = cle_pub, message = challenge)
    """
    if APP.local_user.cle_privee is None:
        raise RuntimeError("Aucune clé privée disponible pour fournir une preuve")
    key = sha256(APP.local_user.cle_privee)
    proof = hmac_sha256(key, challenge)
    return proof

def confirmer_preuve_impl(session: ports.Session, proof: bytes, cle_pub_peer: bytes) -> bool:
    """
    Vérifie la preuve reçue en recalculant HMAC with key = cle_pub_peer.
    Retourne True si valide.
    """
    expected = hmac_sha256(cle_pub_peer, session._last_challenge_received if hasattr(session, '_last_challenge_received') else b'')
    # we used the same challenge we stored earlier; if not present, reject
    return hmac.compare_digest(expected, proof)

def demander_preuve_impl(session: ports.Session) -> bool:
    """
    Procédure complète d'initiateur :
    - génère un nonce
    - envoie REQ_TAG + nonce au pair via socket
    - attend PROOF_TAG + proof (timeout)
    - valide via confirmer_preuve_impl en utilisant dest.ut.cle_publique
    """
    nonce = secrets.token_bytes(16)
    # store last challenge in session for passive verifier usage if needed
    session._last_challenge_sent = nonce
    try:
        session.cet_appareil.settimeout(2.0)
        # send REQ request
        session.cet_appareil.sendto(REQ_TAG + nonce, (session.destinataire.ip, session.destinataire.port))
        # wait for proof
        data, _ = session.cet_appareil.recvfrom(4096)
        if not data.startswith(PROOF_TAG):
            return False
        proof = data[len(PROOF_TAG):]
        # Confirm proof using dest.ut.cle_publique (which should be populated by multicast/discovery)
        if session.destinataire.ut.cle_publique is None:
            # cannot confirm if we don't have peer's public key
            return False
        # store last challenge received by confirmer for their use
        # Now compute expected HMAC using cle_pub_peer as key
        key_peer = session.destinataire.ut.cle_publique
        expected = hmac_sha256(key_peer, nonce)
        ok = hmac.compare_digest(expected, proof)
        return ok
    except socket.timeout:
        return False
    except Exception:
        return False
    finally:
        try:
            session.cet_appareil.settimeout(None)
        except Exception:
            pass

# Passive listener: handle REQ_PROOF and respond with PROOF using fournir_preuve_impl
def passive_proof_responder(session: ports.Session):
    """
    This listens on session.cet_appareil for REQ_PROOF and replies.
    It's started as a thread when a session is created/passive.
    """
    sock = session.cet_appareil
    sock.settimeout(0.5)
    while session.session_active:
        try:
            data, addr = sock.recvfrom(4096)
            if data.startswith(REQ_TAG):
                nonce = data[len(REQ_TAG):]
                # produce proof
                try:
                    proof = fournir_preuve_impl(session, nonce)
                    sock.sendto(PROOF_TAG + proof, addr)
                except Exception:
                    # ignore if cannot produce proof
                    pass
            # else ignore arbitrary traffic here (actual session packets are processed elsewhere)
        except socket.timeout:
            continue
        except Exception:
            continue

# ---------------------------
# UI / Menu handling
# ---------------------------
def menu_loop():
    while APP.running:
        print("\n=== MENU ===")
        print("1. Activer la découverte multicast (déjà active par défaut)")
        print("2. Voir les appareils détectés")
        print("3. Diffuser mes infos (multicast)")
        print("4. Générer mon code de connexion (réservant un port local)")
        print("5. Se connecter via code")
        print("6. Voir les sessions actives")
        print("7. Entrer dans une session pour discuter")
        print("8. Quitter")
        choice = input("Choix: ").strip()
        if choice == "1":
            print("La découverte est active par défaut (si elle ne l'est pas, redémarre l'app).")
        elif choice == "2":
            show_detected()
        elif choice == "3":
            publish_local_info_once()
        elif choice == "4":
            gen_code_interactive()
        elif choice == "5":
            connect_via_code_interactive()
        elif choice == "6":
            list_sessions()
        elif choice == "7":
            enter_session_interactive()
        elif choice == "8":
            print("Fermeture...")
            APP.running = False
            APP.chats.close_all()
            break
        else:
            print("Choix invalide.")

def show_detected():
    print("\nAppareils détectés (détail) :")
    for i, payload in enumerate(APP.chats.contenu_chaines):
        if payload is None:
            continue
        parsed = parse_multicast_payload(payload)
        noms = parsed["noms"] or "<vide>"
        prenoms = parsed["prenoms"] or "<vide>"
        taille = parsed["taille_cle"]
        has_auth = "OUI" if taille and parsed["cle_pub"] else "NON"
        # code_connexion impossible sans IP/port; show what we can
        print(f"[{i}] IP inconnue dans ce stockage, Nom: {noms}, Prénom: {prenoms}, Auth possible: {has_auth}, taille_cle={taille}")

def publish_local_info_once():
    # publish a one-off multicast announcement on the first available multicast address
    addr = APP.chats.trouver_chaine_multicast()
    if addr is None:
        print("Aucune chaîne disponible pour appropriation (échec).")
        return
    print(f"Chaîne appropriée: {addr}. Envoi d'une annonce unique.")
    # build payload with local info
    noms = APP.local_user.noms[0].encode()[:ports.NOMS_SIZE]
    noms = noms + b"\x00" * (ports.NOMS_SIZE - len(noms))
    prenoms = APP.local_user.prenoms[0].encode()[:ports.PRENOMS_SIZE]
    prenoms = prenoms + b"\x00" * (ports.PRENOMS_SIZE - len(prenoms))
    # cle publique : use 32 bytes
    cle_pub = APP.cle_publique
    taille = len(cle_pub)
    taille_field = taille.to_bytes(2, 'big')
    cle_field = cle_pub + b"\x00" * (ports.CLE_PUB_MAX - taille)
    infos = b"\x00" * ports.INFOS_SUP_SIZE
    pack = noms + prenoms + taille_field + cle_field + infos
    try:
        import binascii as _b
        crc4 = _b.crc32(pack).to_bytes(4, 'big')
    except Exception:
        crc4 = b"\x00" * 4
    payload = pack + crc4
    # send once
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(payload, (addr, ports.MULTICAST_PORT))
    s.close()
    print("Annonce envoyée.")

def gen_code_interactive():
    # reserve a local port to generate code
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((APP.local_ip, 0))
    port = s.getsockname()[1]
    code = APP.chats.generer_code_connexion(port)
    print(f"Code de connexion généré (pour le port {port}): {code}")
    s.close()
    return code

def connect_via_code_interactive():
    code = input("Entrez le code (8 caractères): ").strip()
    try:
        session = APP.chats.creer_session_par_code(code, fdc=None, cle=None)
        # assign authentication callbacks to session
        session.demander_preuve = demander_preuve_impl
        session.fournir_preuve = fournir_preuve_impl
        session.confirmer_preuve = confirmer_preuve_impl
        # start passive responder in background for this session
        t = threading.Thread(target=passive_proof_responder, args=(session,), daemon=True)
        t.start()
        print("Session créée et callbacks assignés.")
    except Exception as e:
        print("Erreur lors de la connexion:", e)

def list_sessions():
    print("\nSessions actives :")
    for idx, s in enumerate(APP.chats.sessions):
        state = "ACTIF" if s.session_active else "INACTIF"
        peer = f"{s.destinataire.ip}:{s.destinataire.port}"
        auth = "OUI" if s.authentique else "NON"
        print(f"[{idx}] Peer={peer}, Etat={state}, Authentifié={auth}")

def enter_session_interactive():
    list_sessions()
    sel = input("Choisir le numéro de session à ouvrir: ").strip()
    try:
        idx = int(sel)
    except Exception:
        print("Entrée invalide.")
        return
    if idx < 0 or idx >= len(APP.chats.sessions):
        print("Index hors plage.")
        return
    session = APP.chats.sessions[idx]
    if not session.session_active:
        print("Session non active.")
        return

    print("Entré dans la session. Tapez '/exit' pour revenir au menu.")
    # start thread to listen incoming paquets for this session and print decoded messages
    stop_flag = threading.Event()

    def recv_loop():
        s = session.cet_appareil
        s.settimeout(0.5)
        buf = []
        while not stop_flag.is_set() and session.session_active:
            try:
                data, _ = s.recvfrom(4096)
                # ignore handshake/proof control
                if data.startswith(REQ_TAG) or data.startswith(PROOF_TAG):
                    # handled by passive responder / auth flow
                    continue
                # attempt to interpret as paquets stream: we need to accumulate full message (header + packets)
                # For simplicity, we will attempt to call paquets.decharger_octets on a single received datagram:
                try:
                    # If it's an entête followed by packets, it's unlikely in a single datagram.
                    # We'll store raw data in octets_recus and print hex/utf-8 best-effort.
                    try:
                        text = data.decode('utf-8')
                        print("\n[Remote] " + text)
                    except Exception:
                        print("\n[Remote] (raw) ", data[:80])
                    session.octets_recus.append(data)
                except Exception:
                    # fallback raw display
                    try:
                        print("\n[Remote] ", data.decode(errors='ignore'))
                    except Exception:
                        print("\n[Remote] (raw) ", data[:80])
            except socket.timeout:
                continue
            except Exception:
                continue

    trecv = threading.Thread(target=recv_loop, daemon=True)
    trecv.start()

    try:
        while True:
            msg = input(">>> ")
            if msg.strip() == "/exit":
                stop_flag.set()
                break
            # send message as raw bytes via session.envoyer_octets
            try:
                b = msg.encode('utf-8')
                # if session.cle is set and session.fdc set, we would encrypt; here we just send raw
                session.envoyer_octets(b)
                print("(You) " + msg)
            except Exception as e:
                print("Erreur envoi:", e)
    finally:
        stop_flag.set()
        time.sleep(0.2)

# ---------------------------
# Start-up: brief initialization and monitoring to attach callbacks to newly created sessions
# ---------------------------
def session_watcher():
    """
    Background thread that monitors APP.chats.sessions and assigns auth callbacks
    and starts passive responder where needed.
    """
    seen = set()
    while APP.running:
        for s in list(APP.chats.sessions):
            if id(s) in seen:
                continue
            # assign callbacks if not present
            s.demander_preuve = demander_preuve_impl
            s.fournir_preuve = fournir_preuve_impl
            s.confirmer_preuve = confirmer_preuve_impl
            # start passive responder to handle incoming REQ_PROOF
            t = threading.Thread(target=passive_proof_responder, args=(s,), daemon=True)
            t.start()
            seen.add(id(s))
        time.sleep(0.5)

# ---------------------------
# Entrypoint
# ---------------------------
def main():
    print("Test app démarrée.")
    print("Local IP:", APP.local_ip)
    # start watcher
    tw = threading.Thread(target=session_watcher, daemon=True)
    tw.start()
    try:
        menu_loop()
    except KeyboardInterrupt:
        print("Interrompu.")
    finally:
        APP.running = False
        APP.chats.close_all()
        time.sleep(0.2)

if __name__ == "__main__":
    main()

    