import socket
import threading

class LANClient:
    def __init__(self, message_callback=None):
        self.client_socket = None
        self.is_connected = False
        self.is_running = False
        self.message_callback = message_callback  # Callback pour l'UI

        # Configuration base64 pour les codes de connexion
        self.base_64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?"

    def set_message_callback(self, callback):
        """Définit le callback pour recevoir les messages"""
        self.message_callback = callback

    def decode_connexion_code(self, code: str):
        """Décode le code de connexion base64 en IP et port"""
        try:
            # Convertit chaque caractère en binaire 6 bits
            binary_parts = []
            for char in code:
                if char not in self.base_64:
                    raise ValueError(f"Caractère invalide dans le code: {char}")
                index = self.base_64.index(char)
                binary_parts.append(format(index, '06b'))

            # Combine en chaîne binaire de 48 bits
            bcode = ''.join(binary_parts)

            # Sépare en IP (32 bits) et port (16 bits)
            A = bcode[0:8]  # 8 bits
            B = bcode[8:16]  # 8 bits
            C = bcode[16:24]  # 8 bits
            D = bcode[24:32]  # 8 bits
            p = bcode[32:48]  # 16 bits

            # Convertit en entiers
            ip = f"{int(A, 2)}.{int(B, 2)}.{int(C, 2)}.{int(D, 2)}"
            port = int(p, 2)

            return ip, port

        except Exception as e:
            raise ValueError(f"Code de connexion invalide: {e}")

    def connect_to_server(self, connection_code: str):
        """Se connecte au serveur en plein duplex"""
        try:
            # Décode le code de connexion
            server_ip, server_port = self.decode_connexion_code(connection_code)
            print(f"Connexion a {server_ip}:{server_port}...")

            # Crée le socket client
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)  # Timeout pour la connexion

            # Tentative de connexion
            self.client_socket.connect((server_ip, server_port))
            self.is_connected = True
            self.is_running = True

            print("Connecte au serveur!")

            # Démarre l'écoute des messages du serveur
            listen_thread = threading.Thread(target=self._listen_to_server, daemon=True)
            listen_thread.start()

            return True

        except socket.timeout:
            print("Timeout de connexion - serveur inaccessible")
            return False
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            return False

    def _listen_to_server(self):
        """Écoute les messages du serveur en continu"""
        while self.is_running and self.is_connected:
            try:
                message = self.client_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    print("Deconnecte du serveur")
                    self.is_connected = False
                    break

                print(f"Message recu: {message}")

                # Transmet le message via le callback à l'UI
                if self.message_callback:
                    self.message_callback(message)

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"Erreur ecoute serveur: {e}")
                self.is_connected = False
                break

    def send_message(self, message):
        """Envoie un message au serveur"""
        if self.is_connected and self.client_socket:
            try:
                # S'assurer que le message est encodé correctement
                encoded_message = message.encode('utf-8')
                self.client_socket.send(encoded_message)
                print(f"Message envoye: {message}")
                return True
            except Exception as e:
                print(f"Erreur envoi message: {e}")
                self.is_connected = False
                return False
        else:
            print("Non connecte au serveur")
            return False

    def disconnect(self):
        """Déconnecte le client"""
        self.is_running = False
        self.is_connected = False

        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass

        print("Client deconnecte")

    def get_connection_status(self):
        """Vérifie si le client est connecté"""
        return self.is_connected