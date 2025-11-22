import socket
import netifaces
import time
import threading
import binascii
from typing import Callable, Optional


def trafic_libre(ip, port, duree):
    """
    Detecte si le port d'un peripherique est utilisé pendant
    un temps en ms.
    Retourne faux dès qu'un signal est détecté sur le port
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    
    thread_chrono = threading.Thread(target= time.sleep, args= [duree], daemon=True)
    thread_ecoute = threading.Thread(target = sock.recvfrom, args=[1024], daemon=True)

    thread_chrono.start()
    thread_ecoute.start()

    while True:
        if thread_chrono.is_alive(): # Le temps imparti n'est pas encore fini
            if not thread_ecoute.is_alive(): # Il y'a du traffic sur le port
                sock.close()
                return False
        else: # Le temps imparti est fini sans qu'il y'ai de traffic sur le résau
            sock.close()
            return True
    


def charger_pacquet(id: int, bits: bytes, fdc: Callable = NotImplemented, cle : bytes = bytes(0)):
    """
    Prepare un paquet de bits

    Utilise le CRC-32 pour détecter les 
    collisions d'un packet d'un message.

    Fonction de chiffrement optionelle. 

    Structure d'un packet :
        [Numéro d'ordre: 5 octets] [message: 1431 octets] [CRC: 4 octets]

    
    Args:
        id: la numéro du paquet. Sert à déterminer l'ordre des pacquets.
        bits: une séquence de bits à chiffrer.
        fdc: La fonction de chiffrement qui est AES dans ce projet
        cle: La cle de chiffrement
    Returns:
        Retourne le paquet prêt à l'envoi(et peut être chiffré) 
    """

    nd = id.to_bytes(5, 'big')
    pack = nd + bits
    crc = binascii.crc32(pack).to_bytes(4, 'big')
    bits_pret = pack + crc 

    if fdc != NotImplemented:
        return fdc(bits_pret, cle)
       
    return bits_pret

def charger_octets(octets: bytes, fdc: Callable = NotImplemented, cle : bytes = None, tdc: bytes = b'\x00', infos_sup: bytes=b'\x00\x00\x00\x00'):
    """
    Décompose un série d'occtets en pacquets pour l'envoi

    Utilise le CRC-32 pour détecter les 
    collisions d'un packet d'un message.

    Fonction de chiffrement optionelle. 
    Structure de l'entête:
        [Nombre de paquets: 5 octets] [Nombre d'octets dans le dernier message: 2 octets] [Type de contenu: 1 octet] [Données supplémentaires optionel: 4 octets] [CRC: 4 octets]
    
    Structure d'un packet :
        [Numéro d'ordre: 5 octets] [message: 1431 octets] [CRC: 4 octets]

    
    Args:
        octets: La séquence d'octets dans la message
        fdc: La fonction de chiffrement qui est AES dans ce projet
        cle: La cle de chiffrement
        tdc: Le type de contenu envoyé, O pour une chaine de caractères
        infos_sup: 4 octets supplemantaire pour n'importe quels infos qu'on veut ajouter. Sert aussi a rendre le message de taille 16 octets

    Returns:
        Retourne une liste composé de l'entête puis de paquets du message
    """

    #On commence par diviser la sequence en pacquets de bits
    taille = len(octets)
    ndpn = taille//1431 #Nombre de paquets non fragmentés
    tddp = taille%1431 #Taille du dernier paquet si fragmenté
    ndp = ndpn + (tddp>0)
    entete = ndp.to_bytes(5, 'big')+tddp.to_bytes(2, 'big') + tdc +infos_sup
    crc = binascii.crc32(entete).to_bytes(4,'big')
    
    
    if fdc != NotImplemented:
        entete_charge = fdc(entete+crc,cle)
    else:
        entete_charge = entete + crc
        

    bits_manquant = b'\x00'*((1431-tddp)%1431)
    octets_complet = octets+bits_manquant
    
    return [entete_charge]+[charger_pacquet(i,octets_complet[i*1431:(i+1)*1431],fdc,cle) for i in range(ndp)]
    
class CRCError(Exception):
    """Erreur sur la valeur deu CRC"""
    pass


def sectionner(liste: list, delimiteurs: list[int]):
    """Tranche une liste en sous listes en utilisant les délimiteurs"""
    return [liste[delimiteurs[i]:delimiteurs[i+1]] for i in range(len(delimiteurs)-1)]


def decharger_paquet(paquet: bytes, fdd: Callable = NotImplemented, cle: bytes = None):
    """
    Recupere une série d'octets et retourne une liste contenants
    le numero d'ordre, le méssage et le CRC si le CRC correspond
    """
    if len(paquet) != 1440:
        raise ValueError("La taille du paquet doit être egal à 1440")
    pack = paquet[0:1436] # contenu du paquet sans CRC
    crc = paquet[1436:1440]
    if crc != binascii.crc32(pack).to_bytes(4,'big'):
        raise CRCError("CRC invalide, paquet corrompu")
    else:
        return sectionner(paquet,[0,5,1436,1440])
    

def decharger_entete(entete: bytes):
    """
    Recupere une série d'octets et recupere l'entete du message
    comme liste de ses composants 
    Structure de l'entête:
        [Nombre de paquets: 5 octets] [Nombre d'octets dans le dernier message: 2 octets] [Type de contenu: 1 octet] [Données supplémentaires optionel: 4 octets] [CRC: 4 octets]
    
    """
    if len(entete) != 16:
        raise ValueError("La taille de l'entête doit être de 16 octets")

    pack = entete[0:12]
    crc = entete[12:16]
    if crc != binascii.crc32(pack).to_bytes(4,'big'):
        raise CRCError("CRC invalide, paquet corrompu")
    else:
        return sectionner(entete,[0,5,7,8,12,16])

def decharger_octets(paquets: list[bytes], fdd: Callable = NotImplemented, cle: bytes = None):
    """
    Recupere une liste de paquets et retourne la séquence d'octets
    complète si tous les paquets sont intègres et dans le bon ordre.
    Utilise le CRC-32 pour vérifier l'intégrité des paquets.

    Args:
        paquets: La liste de paquets reçus
        fdd: La fonction de déchiffrement qui est AES dans ce projet
        cle: La cle de déchiffrement
    """
    
    entete = paquets[0]
    entete_decharge = decharger_entete(entete if fdd == NotImplemented else fdd(entete, cle))
    ndp = int.from_bytes(entete_decharge[0], 'big')
    tddp = int.from_bytes(entete_decharge[1], 'big')

    octets_recus = bytearray()

    for i in range(1, ndp + 1):
        paquet = paquets[i]
        paquet_decharge = decharger_paquet(paquet if fdd == NotImplemented else fdd(paquet, cle))
        id_paquet = int.from_bytes(paquet_decharge[0], 'big')
        if id_paquet != i - 1:
            raise ValueError(f"Paquet hors ordre: attendu {i-1}, reçu {id_paquet}")
        octets_recus.extend(paquet_decharge[1])

    return bytes(octets_recus[:(ndp - 1) * 1431 + tddp])

class TimeOutExeption(Exception):
    """Le temps imparti est épuisé"""
    pass



# Cette fonction n'a pas encore été implémenté
def envoyer_octets(octets: bytes, sock_destination: socket.socket, timeout: int, 
                   ecouteur: Callable,fdc: Optional[callable],
                   cle : Optional[bytes],tdc: Optional[bytes], 
                   infos_sup: Optional[bytes]):
    """
    Envoie un message vers une addresse ip et un port bien précis
    l'ecouteur s'excecutera indéfiniment dans un thread pour s'assurer que le méssage
    à bien été recu et informe ce péripherique de la situation des paquets
    envoyés

    On utilisera l'ecouteur pour recevoir les ACKs et les NACKS
    """

    ip, port = sock_destination.getsockname()

    def suivre(situation: bytearray):
        """écoute sur les acks et les nacks envoyés par le port destinataire
        """
        while True:
            pack = sock_destination.recv(2048)
            if len(pack)==6:#Un ACK
                situation = pack
    

            
        
    

