import socket

base_64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?"

def get_local_ip():
    """Get local network IP without internet"""
    try:
        # Try to get IP from network interface
        import netifaces
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if ip.startswith('192.168.') or ip.startswith('10.'):
                        return ip
    except:
        pass
    
    # Fallback: get hostname IP (might be 127.0.0.1)
    return socket.gethostbyname(socket.gethostname())



def start_server(server_ip='', server_port=0):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hostname = socket.gethostname()
    print(f"Host: {hostname}")
    assigned_port = 0
    try:
        server_socket.bind((server_ip, server_port))
        assigned_ip = server_socket.getsockname()[0]
        assigned_port = server_socket.getsockname()[1]
        print(f"Server successfully bound to port {assigned_port}")
    except OSError as e:
        print(f"Failed to bind server on port {server_port}: {e}")
        return
    server_socket.listen(1)
    print(f"Server's IP address: {assigned_ip}")
    print(f"Server listening on port {assigned_port}...")
    print(f"Connexion code = {encode_connexion_code(assigned_ip,assigned_port)}")

    try:
        client_socket, client_address = server_socket.accept()
        print(f"Connection accepted from {client_address}")
        client_socket.sendall(b"Hello, you are connected to the server!\n")
        while True:
            start_chat(client_socket)
            
    except KeyboardInterrupt:
        print("Server is shutting down.")
    finally:
        server_socket.close()


def start_chat(client_socket: socket):
    """Chat logic, must match clietnt chat logic to work properly"""
    client_message = client_socket.recv(1024).decode()
    print(f"Client: {client_message}")
    server_message = input("Message for client: ")
    client_socket.sendall(f"Server: {server_message}".encode())

def encode_connexion_code(ip :str ,port):
    """
    Uses the IP address and the port address of the current device and maps
    it to a base 64 system(0-9,A-Z,a-z,!,?) which will result in 8 characters.
    """
    A,B,C,D = ['','','','']
    if ip == 'localhost':
        A,B,C,D = [format(a, "b").zfill(8) for a in [127, 0, 0, 1]]
    else:
        A,B,C,D = [format(int(a),"b").zfill(8) for a in ip.split('.')]

    p=format(int(port),"b").zfill(16)
    bcode = A+B+C+D+p
    code=[]
    for i in range(8):
        code.append(bcode[6*i:6*(i+1)]) #bcode[0:5] , bcode[6-11],...,bcode[42-47]
    
    connection_code = "".join([str(base_64[int(bits,2)]) for bits in code])

    return connection_code


start_server(get_local_ip())
