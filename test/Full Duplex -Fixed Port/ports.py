import socket
from typing import List
from typing import Optional
# Plage multicast privée:
# "239.192.1.1" à "239.192.2.45"

# Soit 301 adresses :
base = "239.192.{}"
adresses = []

for troisieme_octet in range(1, 3):  # 1 et 2
    for quatrieme_octet in range(1, 256):
        if len(adresses) >= 301:
            break
        adresses.append(base.format(f"{troisieme_octet}.{quatrieme_octet}"))

# Décommentez pour voir le résultat
# print(adresses)
# print(type(adresses))

class utilisateur:
    def _init_(self, noms: List[str], prenoms: List[str], signature_mayo: Optional[bytes]):
        self.noms = noms
        self.prenoms = prenoms
        if signature_mayo != None:
            self.signature_mayo = signature_mayo
    
    
class appareil:
    def __init__(self, ip: str, port: int, ut: utilisateur):
        self.ip = ip
        self.port = port
        self.ut = utilisateur

    

    