import threading
import time
import socket
import sys

from ports import Chats, Utilisateur, Session

# ---------------------------------------------------------------------------
# AES interne factice (remplacée plus tard par la vraie)
# ---------------------------------------------------------------------------

def fdc_aes_interne(octets: bytes, cle: bytes) -> bytes:
    """AES interne minimal (réversible bitwise-xor).
    Cette version est juste pour TESTER le protocole. À remplacer par AES réel."""
    if not cle:
        return octets
    out = bytearray()
    for i, b in enumerate(octets):
        out.append(b ^ cle[i % len(cle)])
    return bytes(out)


# ---------------------------------------------------------------------------
# Config utilisateur pour le test
# ---------------------------------------------------------------------------

CURRENT_USER = Utilisateur(
    noms=["Alice"],
    prenoms=["Test"],
    cle_publique=b"",     # 0 signifie pas d’auth obligatoire
    cle_privee=None       # pas utilisé dans ce test
)


# ---------------------------------------------------------------------------
# APP global
# ---------------------------------------------------------------------------

APP = None      # sera instancié au lancement
RUNNING = True


# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

def print_menu():
    print("\n=== MENU ===")
    print("1. Voir les appareils détectés (CRC valides)")
    print("2. Diffuser mes infos (multicast)")
    print("3. Se connecter via multicast (par index)")
    print("4. Voir les sessions actives")
    print("5. Entrer dans une session pour discuter")
    print("6. Quitter")
    print("Choix: ", end="", flush=True)


# ---------------------------------------------------------------------------
# Option 1 : Affichage des appareils détectés
# ---------------------------------------------------------------------------

def show_detected():
    print("\n=== Appareils détectés ===")
    for i, entry in enumerate(APP.contenu_chaines):
        if entry is None:
            continue
        p = entry["parsed"]
        print(f"[{i}] {p['noms']} {p['prenoms']}")
        print(f"     IP   : {entry['ip']}")
        print(f"     Port : {entry['port']}")
        print(f"     Cle  : taille={p['taille_cle']} octets")
        print()
    print("=== FIN ===")


# ---------------------------------------------------------------------------
# Option 2 : Diffuser une annonce unique
# ---------------------------------------------------------------------------

def broadcast_once():
    print("\nEnvoi d'une annonce unique sur TOUTES les chaînes…")
    for addr in APP.contenu_chaines:
        pass
    # En réalité, on diffuse sur 1 chaîne choisie : test simple:
    # Utilise l'adresse choisie dans APP.chaine_multicast, sinon fixe
    adresse = APP.chaine_multicast or "239.192.1.1"
    try:
        APP.publier_message_sur_chaine_onadresse(
            adresse,
            noms="Alice".encode(),
            prenoms="Test".encode(),
            cle_pub=None,
            port_reception=APP.sock_de_recherche.getsockname()[1],
        )
        print("Annonce envoyée.")
    except Exception as e:
        print("Erreur broadcast:", e)


# ---------------------------------------------------------------------------
# Option 3 : Connexion directe via multicast
# ---------------------------------------------------------------------------

def connect_from_detected():
    try:
        index = int(input("Index dans la liste détectée: "))
    except:
        print("Index invalide.")
        return
    try:
        session = APP.creer_session_par_multicast(
            index=index,
            fdc=fdc_aes_interne,
            cle=b"ma_cle_interne_test"
        )
        print("Session créée avec succès.")
    except Exception as e:
        print("ERREUR:", e)


# ---------------------------------------------------------------------------
# Option 4 : Lister les sessions
# ---------------------------------------------------------------------------

def show_sessions():
    print("\n=== Sessions actives ===")
    for i, s in enumerate(APP.sessions):
        print(f"[{i}] -> {s.destinataire.ip}:{s.destinataire.port}  actif={s.session_active}")
    print("=== FIN ===")


# ---------------------------------------------------------------------------
# Option 5 : Discussion dans une session
# ---------------------------------------------------------------------------

def chat_in_session():
    try:
        idx = int(input("Numéro de session: "))
    except:
        print("Index invalide.")
        return

    if idx < 0 or idx >= len(APP.sessions):
        print("Aucune session à cet index.")
        return

    sess = APP.sessions[idx]

    print(f"\n=== Session avec {sess.destinataire.ip}:{sess.destinataire.port} ===")
    print("Tapez /exit pour revenir au menu.")
    print("----------------------------------------")

    # Thread non bloquant pour réception interne
    def receiver():
        while RUNNING and sess.session_active:
            try:
                data, _ = sess.cet_appareil.recvfrom(4096)
                # Décode les paquets (format paquets.py)
                print("\n(Recep) Octets bruts reçus:", len(data))
                print(">>> ", end="", flush=True)
            except:
                time.sleep(0.1)

    t = threading.Thread(target=receiver, daemon=True)
    t.start()

    # Boucle d’envoi
    while True:
        msg = input(">>> ")
        if msg == "/exit":
            print("Retour au menu.")
            return
        try:
            sess.ajouter_message_a_envoyer(msg.encode())
        except Exception as e:
            print("Erreur envoi:", e)


# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

def main():
    global APP, RUNNING

    # Initialise la pile Chat
    APP = Chats()

    print("\nSystème démarré. Multicast actif. Recherche de pairs…")
    time.sleep(1)

    while RUNNING:
        print_menu()
        choice = input("").strip()

        if choice == "1":
            show_detected()

        elif choice == "2":
            broadcast_once()

        elif choice == "3":
            connect_from_detected()

        elif choice == "4":
            show_sessions()

        elif choice == "5":
            chat_in_session()

        elif choice == "6":
            print("Fermeture…")
            RUNNING = False
            break

        else:
            print("Choix invalide.")

    try:
        APP.close_all()
    except:
        pass


if __name__ == "__main__":
    main()