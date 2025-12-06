import socket
import threading
import time


def get_local_ip():
    """Get local IP address"""
    try:
        # Create a temporary socket to get local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def encode_connexion_code(ip: str, port: int):
    """Encode IP and port to base64 connection code"""
    base_64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?"

    if ip == 'localhost':
        A, B, C, D = [format(a, "b").zfill(8) for a in [127, 0, 0, 1]]
    else:
        A, B, C, D = [format(int(a), "b").zfill(8) for a in ip.split('.')]

    p = format(int(port), "b").zfill(16)
    bcode = A + B + C + D + p
    code = []
    for i in range(8):
        code.append(bcode[6 * i:6 * (i + 1)])

    connection_code = "".join([str(base_64[int(bits, 2)]) for bits in code])
    return connection_code


class LANServer:
    def __init__(self):
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.is_running = False
        self.message_callback = None
        self.connection_callback = None  # Ajoutez cette ligne

    def set_message_callback(self, callback):
        """Set callback for received messages"""
        self.message_callback = callback

    def wait_for_connection(self, callback):
        """Attend une connexion et appelle le callback quand un client se connecte"""
        self.connection_callback = callback

    def set_message_callback(self, callback):
        """Set callback for received messages"""
        self.message_callback = callback

    def start_server(self, ip='', port=0):
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket
            self.server_socket.bind((ip, port))
            assigned_ip = self.server_socket.getsockname()[0]
            assigned_port = self.server_socket.getsockname()[1]

            print(f" Server started on {assigned_ip}:{assigned_port}")
            print(f" Connection code: {encode_connexion_code(assigned_ip, assigned_port)}")

            # Listen for connections
            self.server_socket.listen(1)
            self.is_running = True

            # Start accepting connections in a thread
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()

            return True, assigned_ip, assigned_port

        except Exception as e:
            print(f" Server start error: {e}")
            return False, None, None

    def _listen_to_client(self):
        """Listen to client messages"""
        while self.is_running and self.client_socket:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    print("Client disconnected")
                    self.client_socket = None
                    self.client_address = None
                    break

                print(f"Message received: {message}")

                # Forward message via callback - IMPORTANT: Appeler le callback
                if self.message_callback:
                    self.message_callback(message)

            except Exception as e:
                if self.is_running:
                    print(f"Client listen error: {e}")
                break

    def _accept_connections(self):
        """Accept incoming connections"""
        while self.is_running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, client_address = self.server_socket.accept()

                print(f"Connection accepted from {client_address}")
                self.client_socket = client_socket
                self.client_address = client_address

                # CORRECTION: Appeler le callback avec l'adresse formatée
                if self.connection_callback:
                    # Formater l'adresse en string
                    formatted_address = f"{client_address[0]}:{client_address[1]}"
                    print(f"DEBUG: Calling connection callback: {formatted_address}")
                    self.connection_callback(formatted_address)
                else:
                    print("DEBUG: No connection callback set!")

                # Start listening to client messages
                listen_thread = threading.Thread(target=self._listen_to_client, daemon=True)
                listen_thread.start()

                # Send welcome message (sans émoji)
                self.send_message("Server: Welcome to LAN Chat!")

            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"Connection error: {e}")
    def _listen_to_client(self):
        """Listen to client messages"""
        while self.is_running and self.client_socket:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    print("Client disconnected")
                    self.client_socket = None
                    self.client_address = None
                    break

                print(f"Message received from client: {message}")

                # CORRECTION: Bien vérifier et appeler le callback
                if self.message_callback:
                    print(f"DEBUG: Calling message callback with: {message}")
                    self.message_callback(message)
                else:
                    print("DEBUG: No message callback set!")

            except Exception as e:
                if self.is_running:
                    print(f"Client listen error: {e}")
                break
    def send_message(self, message):
        """Send message to connected client"""
        if self.client_socket:
            try:
                # Vérifier que le socket est toujours connecté
                try:
                    # Test rapide pour voir si le socket est toujours valide
                    self.client_socket.getpeername()
                except (socket.error, OSError):
                    print("Client socket is no longer connected")
                    self.client_socket = None
                    return False

                self.client_socket.send(message.encode('utf-8'))
                print(f"Message sent: {message}")
                return True  # IMPORTANT: Retourner True si réussi

            except Exception as e:
                print(f"Message send error: {e}")
                self.client_socket = None
                return False
        else:
            print("No client connected")
            return False
    def stop_server(self):
        """Stop the server"""
        self.is_running = False

        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        print(" Server stopped")

    def is_client_connected(self):
        """Check if client is connected"""
        return self.client_socket is not None