import socket

base_64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!?"

def decode_connexion_code(code: str):
    """Decodes 8-character base64 code back to IP and port"""
    # Convert each character to 6-bit binary
    binary_parts = []
    for char in code:
        index = base_64.index(char)
        binary_parts.append(format(index, '06b'))
    
    # Combine all 8 parts into 48-bit string
    bcode = ''.join(binary_parts)
    
    # Split into IP parts (32 bits) and port (16 bits)
    A = bcode[0:8]    # 8 bits
    B = bcode[8:16]   # 8 bits  
    C = bcode[16:24]  # 8 bits
    D = bcode[24:32]  # 8 bits
    p = bcode[32:48]  # 16 bits
    
    # Convert binary to integers
    ip = f"{int(A, 2)}.{int(B, 2)}.{int(C, 2)}.{int(D, 2)}"
    port = int(p, 2)
    
    return ip, port

def start_client(connection_code: str):
    """Connect to server using connection code"""
    # Decode the connection code
    server_ip, server_port = decode_connexion_code(connection_code)
    print(f"Connecting to {server_ip}:{server_port}...")
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((server_ip, server_port))
        print("✅ Connected to server!")
        
        # Receive welcome message
        welcome = client_socket.recv(1024).decode()
        print(f"Server: {welcome}")
        
        # Half-duplex chat loop (same pattern as server)
        while True:
            # Client sends first
            client_message = input("You: ")
            client_socket.send(client_message.encode())
            if client_message.lower() == 'quit':
                break
            
            # Then receive server response
            server_message = client_socket.recv(1024).decode()
            print(f"Server: {server_message}")
            if "quit" in server_message.lower():
                break
                
    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client_socket.close()
        print("🔴 Disconnected")

# Run client
if __name__ == "__main__":
    code = input("Enter connection code: ").strip()
    start_client(code)