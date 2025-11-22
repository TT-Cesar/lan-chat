import socket
import secrets
import paquets
import threading
import queue
from typing import Callable, List,Optional

# Nombre premier sécurisé de 2048 bits (RFC 3526)
p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF

g = 2  # Générateur

# Plage multicast privée:
# "239.192.1.1" à "239.192.2.45"

# Soit 301 adresses :
base = "239.192.{}"
adresses_multicast = []

for troisieme_octet in range(1, 3):  # 1 et 2
    for quatrieme_octet in range(1, 256):
        if len(adresses_multicast) >= 301:
            break
        adresses_multicast.append(base.format(f"{troisieme_octet}.{quatrieme_octet}"))

# Décommentez pour voir le résultat
# print(adresses)
# print(type(adresses))

ports_decoutes= [
    54321,  
    58732,  # Les ports sur lesquels les appareils
    61248,  # s'identifient régulièrement
    49876,  
    52413,  
    59987,  
    63254,  
    50789,  
    57801,  
    64523   
]

class Utilisateur:
    def _init_(self, noms: List[str], prenoms: List[str], cle_publique: Optional[bytes]):
        self.noms = noms
        self.prenoms = prenoms
        if cle_publique != None:
            self.cle_publique = cle_publique
    
class Appareil: # Représente un autre appareil sur le réseau
    def __init__(self, ip: str, port: int, ut: Utilisateur, octets_envoyes: List[bytes], octets_recus: List[bytes]):
        self.sock_recep = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(ip,port)
        self.ip = ip
        self.port = port
        self.ut = Utilisateur

class Session:
    def _init_(self,sock_reception: socket.socket,  destinataire: Appareil, fdc: Optional[callable], cle: Optional[bytes]):
        self.cet_appareil = sock_reception
        self.destinataire = destinataire
        if fdc != None and cle != None:
            self.fdc = fdc
            self.cle = cle
        self.octets_envoyes = []
        self.octets_recus = []
        self.octets_a_envoyer = queue.Queue() # Octets prêts à être envoyés
        self.octets_a_recevoir = queue.Queue() # Octets prêts à être reçus
        self.session_active = False
        self.ACK_session = b'0x01' # Ici la taille du ACH c'est juste un octet
        self.ACK_entete = b'0x02'   # Ici, la taille du ACK c'est aussi juste un octet
        self.ACK_paquet = b'0x03'  # Ceci n'est que le debut du ACK d'un paquet. En réalité sa taille est de 6 octets(1 pour le code ACK + 5 pour l'ID du paquet)
        self.NACK_paquet = b'0x30' # Même structure que le ACK d'un paquet, sera envoyé si un paquet n'est pas reçu correctement ou n'est pas récu après un certain temps(1 seconde ici)
    
    def envoyer_octets(self, octets: bytes, fdc: Callable = NotImplemented, cle : bytes = None, tdc: bytes = b'\x00', infos_sup: bytes=b'\x00\x00\x00\x00'):
        """Envoi des données au destinataire"""
        paquets_a_envoyer = paquets.charger_octets(octets, fdc, cle, tdc, infos_sup)
        for paquet in paquets_a_envoyer:
            self.destinataire.sock.sendto(paquet, (self.destinataire.ip, self.destinataire.port))
    
    def recevoir_octets(self, paquets: List[bytes], fdd: Callable = NotImplemented, cle: bytes = None) -> bytes:
        """Reçoit des paquets et reconstitue les octets d'origine
    Args:
        paquets: La liste de paquets reçus
        fdd: La fonction de déchiffrement qui est AES dans ce projet
        cle: La cle de déchiffrement
    """
    
        entete = paquets[0]
        entete_decharge = paquets.decharger_entete(entete if fdd == NotImplemented else fdd(entete, cle))
        ndp = int.from_bytes(entete_decharge[0], 'big')
        tddp = int.from_bytes(entete_decharge[1], 'big')

        octets_recus = bytearray()

        for i in range(1, ndp + 1):
            paquet = paquets[i]
            paquet_decharge = paquets.decharger_paquet(paquet if fdd == NotImplemented else fdd(paquet, cle))
            id_paquet = int.from_bytes(paquet_decharge[0], 'big')
            if id_paquet != i - 1:
                raise ValueError(f"Paquet hors ordre: attendu {i-1}, reçu {id_paquet}")
            octets_recus.extend(paquet_decharge[1])

        return bytes(octets_recus[:(ndp - 1) * 1431 + tddp])
    
    def thread_envoi(self):
        """Thread pour envoyer des octets en arrière-plan"""
        while True:
            try:
                octets = self.octets_a_envoyer.get(timeout=1)  # Attendre jusqu'à 1 seconde pour obtenir des octets
                self.envoyer_octets(octets, self.fdc, self.cle)
            except queue.Empty:
                continue  # Pas d'octets à envoyer, continuer la boucle
            

    def _echange_cle(self):
        """Utilise Diffie Hellman pour implementer l'echange de clés"""
        def envoyer_cle():
            """Envoie la clé publique à l'autre appareil"""
            a = secrets.randbelow(p-2) + 1  # 1 <= a <= p-2
            A = pow(g, a, p)  # Calcul de la clé publique
            # Envoi de A à l'autre appareil
            self.cet_appareil.sock.sendto(A.to_bytes((A.bit_length() + 7) // 8, 'big'), (self.destinataire.ip, self.destinataire.port))
            return a, A
        def recevoir_cle():
            """Reçoit la clé publique de l'autre appareil"""
            data, _ = self.cet_appareil.sock.recvfrom(4096)
            B = int.from_bytes(data, 'big')
            return B
        def calculer_cle_secrete(a, B):
            """Calcule la clé secrète partagée"""
            K = pow(B, a, p)
            return K.to_bytes((K.bit_length() + 7) // 8, 'big')
        a, A = envoyer_cle()
        B = recevoir_cle()
        cle_secrete = calculer_cle_secrete(a, B)
        return cle_secrete


    def envoyer_ACK_session(self):
        """Envoie un ACK au destinataire pour établir la session"""
        self.destinataire.sock.sendto(self.ACK_session, (self.destinataire.ip, self.destinataire.port))

    def recevoir_ACK_session(self):
        """Attend et reçoit un ACK du destinataire pour établir la session"""
        self.cet_appareil.sock.settimeout(1)  # Timeout de 1 seconde
        data, _ = self.cet_appareil.sock.recvfrom(1) # Taille de l'ACK
        if data == self.ACK_session:
            return True
        return False

    def envoyer_ACK_entete(self):
        """
        Demande confirmation qu l'entête d'un méssage à été
        envoyé
        """
        self.destinataire.sock.sendto(0x01.to_bytes(1,'big'), (self.destinataire.ip, self.destinataire.port))




    def envoyer_octets(self, octets: bytes, fdc: Callable = NotImplemented, cle : bytes = None, tdc: bytes = b'\x00', infos_sup: bytes=b'\x00\x00\x00\x00'):
        """Envoi des données au destinataire"""
        paquets_a_envoyer = paquets.charger_octets(octets, fdc, cle, tdc, infos_sup)
        for paquet in paquets_a_envoyer:
            self.destinataire.sock.sendto(paquet, (self.destinataire.ip, self.destinataire.port))
        


    def creer_session(self):
        """
        Crée une session entre 2 appareils
        """
        self.envoyer_ACK_session()
        if not self.recevoir_ACK_session():
            self.destinataire.sock.close()
            self.cet_appareil.sock.close()
            del self # Supprime la session en cas d'échec
            raise ConnectionError("Échec de l'établissement de la session : ACK non reçu.")
        
        # A ce stade, la session est établie
        self.session_active = True
        if self.fdc != None and self.cle != None:
            cle_secrete = self._echange_cle()
            # Initialiser le chiffrement avec cle_secrete
            # (Implémentation du chiffrement non incluse ici)

        
        

class Chats:
    def _init_(self,ip: str, sessions: List[Session]=[], etats_chaines: List[bytes] = []):
        self.ip = ip
        self.sessions = sessions
        self.etats_chaines = etats_chaines
        self.socks_de_recherche = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Socket pour l'écoute des chaines multicast
        self.socks_reception = [] # Sockets pour la reception des données des sessions actives
                                  # Le dernier socket de cette liste est toujours réservé pour la prochaine session créée.
        for port in ports_decoutes:
            try:
                self.socks_de_recherche.bind((ip,port))
                break
            except OSError:
                if port == ports_decoutes[-1]:
                    raise OSError("Aucun port d'écoute disponible.")
                else:
                    print (f"Le port {port} est déjà utilisé, essayant le suivant...")
                    continue
        
        # Après avoir créé le sock de recherche, on le fait rejoindre les groupes multicast
        for adresse in adresses_multicast:
            mreq = socket.inet_aton(adresse) + socket.inet_aton(ip)
            self.socks_de_recherche.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    def ajouter_port_libre(self):
        """
        Ajoute un port libre à la liste des sockets de réception
        """
        sock_libre = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_libre.bind((self.ip,0)) # Laisse le système assigner un port libre
        self.socks_reception.append(sock_libre)

        


    def actualiser_etat_chaines():
        """
        Vérifie les chaines multicast pour savoir
        les utilisateurs actifs sur le réseau.
        Sert aussi à savoir si une addresse est libre.
        Sera appelé en boucle toutes les x secondes si la
        detection passive est activée et à la création du chat.
        Pourra aussi être activé manuellement par l'utilisateur.

        Structure d'un message de chaine multicast :
        [Nom(s): 200 octets] [Prénom(s):[Nom(s): 200 octets] [Prénom 200 octets] [taille de la clé publique: 2 octets] [Clé publique: 1024 octets] [infos sup: 44 octets] Total: 1470 octets

        Chaque chaine attendra 250ms apres chaque envoi de son statut

        """

        



        



        
