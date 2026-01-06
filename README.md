# lan-chat
Projet de SI portant sur la création d'une application de méssagerie qui utilise le protocole de Diffie-Hellman pour l'échange des clés et l'AES pour le chiffrement. Les messages seront envoyés entre 2 machines connectés sur un même réseau local(LAN) comme un hotspot ou un modem.

## Lancement
    L'executable est déjà compilé et dans le dossier "./dist"

### Windows
Double-cliquer sur le fichier `LocalWhisper.exe` dans le dossier `./dist`.

### Linux(Ubuntu/Debian)
Ouvrir un terminal et naviguer jusqu'au dossier `./dist`, puis exécuter la commande :
```bash
./LocalWhisper
```

## Utilisation
1. Démarrer l'application sur deux machines connectées au même réseau local.
2. Créer un salon sur la première machine puis copier le code de connexion.
3. Sur la deuxième machine, rejoindre le salon en recopiant le code de connexion.
4. Commencer à échanger des messages de manière sécurisée !