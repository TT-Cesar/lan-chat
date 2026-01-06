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
    noms=["Host"],
    prenoms=["Test"],
    cle_publique=b"",     # 0 signifie pas d'auth obligatoire
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
    print("2. Forcer appropriation d'une chaîne multicast")
    print("3. Se connecter via multicast (par index)")
    print("4. Voir les sessions actives")
    print("5. Entrer dans une session pour discuter")
    print("6. Générer code de connexion")
    print("7. Quitter")
    print("Choix: ", end="", flush=True)


# ---------------------------------------------------------------------------
# Option 1 : Affichage des appareils détectés
# ---------------------------------------------------------------------------

def show_detected():
    print("\n=== Appareils détectés ===")
    detected_count = 0
    for i, entry in enumerate(APP.contenu_chaines):
        if entry is None:
            continue
        p = entry["parsed"]
        print(f"[{i}] {p['noms']} {p['prenoms']}")
        print(f"     IP   : {entry['ip']}")
        print(f"     Port : {entry['port']}")
        print(f"     Cle  : taille={p['taille_cle']} octets")
        print(f"     Dernière vue : {time.time() - entry['last_seen']:.1f}s")
        print()
        detected_count += 1
    
    if detected_count == 0:
        print("Aucun appareil détecté.")
        print("Assurez-vous que d'autres instances sont en cours d'exécution sur le même réseau.")
    print("=== FIN ===")


# ---------------------------------------------------------------------------
# Option 2 : Forcer l'appropriation d'une chaîne
# ---------------------------------------------------------------------------

def force_multicast_appropriation():
    print("\nForcer l'appropriation d'une chaîne multicast…")
    
    # Arrêter la diffusion actuelle si elle existe
    old_chain = APP.chaine_multicast
    APP.chaine_multicast = None
    
    # Trouver une nouvelle chaîne
    chaine = APP.trouver_chaine_multicast(
        noms=b"Host",
        prenoms=b"Test", 
        cle_pub=None,
        port_reception=APP.port_p2p
    )
    
    if chaine:
        print(f"✅ Chaîne appropriée : {chaine}")
        print(f"✅ Port P2P : {APP.port_p2p}")
        if old_chain:
            print(f"✅ Ancienne chaîne {old_chain} libérée")
    else:
        print("❌ Aucune chaîne libre trouvée")
        APP.chaine_multicast = old_chain  # Restaurer l'ancienne


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
        print("✅ Session créée avec succès.")
        print(f"✅ Avec {session.destinataire.ip}:{session.destinataire.port}")
    except Exception as e:
        print(f"❌ ERREUR: {e}")


# ---------------------------------------------------------------------------
# Option 4 : Lister les sessions
# ---------------------------------------------------------------------------

def show_sessions():
    print("\n=== Sessions actives ===")
    active_sessions = APP.liste_sessions_actives()
    
    if not active_sessions:
        print("Aucune session active.")
    else:
        for i, s in enumerate(active_sessions):
            status = "✅ Authentique" if s.authentique else "❌ Non authentique"
            print(f"[{i}] {s.destinataire.ip}:{s.destinataire.port} - {status}")
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

    active_sessions = APP.liste_sessions_actives()
    if idx < 0 or idx >= len(active_sessions):
        print("Aucune session à cet index.")
        return

    sess = active_sessions[idx]

    print(f"\n=== Session avec {sess.destinataire.ip}:{sess.destinataire.port} ===")
    print("Tapez /exit pour revenir au menu.")
    print("----------------------------------------")

    # Thread pour la réception des messages
    def receiver():
        while RUNNING and sess.session_active:
            try:
                data, addr = sess.cet_appareil.recvfrom(4096)
                # Vérifier que le message vient du bon destinataire
                if addr[0] == sess.destinataire.ip and addr[1] == sess.destinataire.port:
                    try:
                        # Essayer de déchiffrer et afficher le message
                        message = data.decode('utf-8', errors='ignore')
                        print(f"\n[Message reçu] {message}")
                        print(">>> ", end="", flush=True)
                    except Exception as e:
                        print(f"\n[Données brutes reçues] {len(data)} octets")
                        print(">>> ", end="", flush=True)
            except socket.timeout:
                continue
            except Exception as e:
                if RUNNING:  # Ne pas afficher l'erreur si on quitte normalement
                    print(f"\nErreur réception: {e}")
                break

    # Configurer le timeout pour la réception
    sess.cet_appareil.settimeout(0.5)
    
    # Démarrer le thread de réception
    t = threading.Thread(target=receiver, daemon=True)
    t.start()

    # Boucle d'envoi
    while RUNNING and sess.session_active:
        try:
            msg = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            break
            
        if msg == "/exit":
            print("Retour au menu.")
            break
            
        if msg.strip():  # Ne pas envoyer de message vide
            try:
                # Utiliser la file d'envoi de la session
                sess.octets_a_envoyer.put(msg.encode('utf-8'))
                print("[Message envoyé]")
            except Exception as e:
                print(f"Erreur envoi: {e}")


# ---------------------------------------------------------------------------
# Option 6 : Générer code de connexion
# ---------------------------------------------------------------------------

def generate_connection_code():
    try:
        code = APP.generer_code_connexion()
        print(f"\n=== Code de connexion ===")
        print(f"Code : {code}")
        print(f"IP : {APP.ip}")
        print(f"Port P2P : {APP.port_p2p}")
        print("Partagez ce code pour permettre la connexion directe.")
        print("=== FIN ===")
    except Exception as e:
        print(f"❌ Erreur génération code: {e}")

# In test.py

def main():
    global APP, RUNNING, CURRENT_USER

    # --- NEW: User Input for Name ---
    print("\n=== CONFIGURATION ===")
    my_name = input("Entrez votre nom (ex: Host): ").strip()
    if not my_name: my_name = "Host"
    my_surname = input("Entrez votre prenom (ex: Test): ").strip()
    if not my_surname: my_surname = "Test"
    
    CURRENT_USER = Utilisateur(
        noms=[my_name],
        prenoms=[my_surname],
        cle_publique=b"",
        cle_privee=None
    )
    # --------------------------------

    try:
        # Pass CURRENT_USER to Chats so it uses the right name in multicast
        APP = Chats(multicast_active=True)
        
        print("\n✅ Système démarré avec succès!")
        print(f"✅ Identité: {my_name} {my_surname}")
        print(f"✅ IP locale: {APP.ip}")
        print(f"✅ Port P2P: {APP.port_p2p}")
        print(f"✅ Chaîne multicast: {APP.chaine_multicast}")
    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")
        return

    # ... rest of the main loop ...

if __name__ == "__main__":
    main()