import socket
import netifaces
import time
import threading
import binascii
from typing import Callable


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
    Prepare un pacquet de bits

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
        [Nombre de packets: 5 octets] [Nombre d'octets dans le dernier message: 2 octets] [Type de contenu: 1 octet] [Données supplémentaires optionel: 4 octets] [CRC: 4 octets]
    
    Structure d'un packet :
        [Numéro d'ordre: 5 octets] [message: 1431 octets] [CRC: 4 octets]

    
    Args:
        octets: La séquence d'octets dans la message
        fdc: La fonction de chiffrement qui est AES dans ce projet
        cle: La cle de chiffrement
        tdc: Le type de contenu envoyé, O pour une chaine de caractères
        infos_sup: 4 octets supplemantaire pour n'importe quels infos qu'on veut ajouter. Sert aussi a rendre le message de taille 16 octets

    Returns:[charger_p
        Retourne une liste composé de l'entête puis de packets du message
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
    

