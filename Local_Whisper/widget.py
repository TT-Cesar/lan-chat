# This Python file uses the following encoding: utf-8
import sys
import threading
import socket
import time
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QInputDialog, QLabel
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QClipboard
from ui_secondpage import Ui_Form as Ui_SecondPage
from ui_SecondPage2 import Ui_Form as Ui_SecondPage2
from ui_messagepage import Ui_Form as Ui_MessagePage
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QInputDialog, QLabel, QFrame, QVBoxLayout, QHBoxLayout,QTextEdit
from PySide6.QtCore import QObject, Signal, QTimer, Qt

from ui_form import Ui_Widget

# Importez seulement LANServer - les fonctions sont maintenant dans server.
# Remplacer cette ligne :
# from server import get_local_ip, encode_connexion_code

# Par :
from server import get_local_ip, encode_connexion_code, LANServer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QTextEdit
from PySide6.QtCore import Qt, QTimer
# Dans widget.py, ajoutez cet import avec les autres
from client import LANClient



class ServerSignals(QObject):
    code_ready = Signal(str, str, str)  # code, ip, port
    client_connected = Signal(str)  # adresse du client
    error_occurred = Signal(str)  # message d'erreur

class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)

        self.server = None
        self.client = None
        self.server_thread = None
        self.client_thread = None
        self.server_signals = ServerSignals()
        self.second_page = None
        self.message_page = None

        # Connecte les signaux du serveur
        self.server_signals.code_ready.connect(self.on_code_ready)
        self.server_signals.client_connected.connect(self.on_client_connected)  # AJOUT IMPORTANT
        self.server_signals.error_occurred.connect(self.on_server_error)

        if hasattr(self.ui, 'pushButton'):
            self.ui.pushButton.clicked.connect(self.open_second_page)
        if hasattr(self.ui, 'pushButton_2'):
            self.ui.pushButton_2.clicked.connect(self.open_second_page2)

        # Si tu as un bouton pour rejoindre un salon, connecte-le aussi

    def open_second_page(self):
        """Ouvre la seconde page en cachant la principale et lance le serveur"""
        self.second_page = SecondPage(self)
        self.second_page.show()
        self.hide()

        # Lance le serveur
        self.lancer_serveur()
    def open_second_page2(self):
        """Ouvre la seconde page en cachant la principale et lance le serveur"""
        self.second_page2 = SecondPage2(self)
        self.second_page2.show()
        self.hide()

    def lancer_serveur(self):
        """Lance le serveur dans un thread séparé"""
        print("Démarrage du serveur...")

        self.server_thread = threading.Thread(target=self._lancer_serveur_thread, daemon=True)
        self.server_thread.start()

    def _lancer_serveur_thread(self):
        """Fonction exécutée dans le thread serveur"""
        try:
            self.server = LANServer()

            # CORRECTION: Définir le callback pour les messages AVANT de démarrer le serveur
            self.server.set_message_callback(self.on_message_received)

            success, ip, port = self.server.start_server(get_local_ip())

            if success:
                code = encode_connexion_code(ip, port)
                print(f"DEBUG: Code généré: {code}, IP: {ip}, Port: {port}")
                self.server_signals.code_ready.emit(code, ip, str(port))

                # Configure le callback de connexion
                self.server.wait_for_connection(self.on_client_connected_callback)
            else:
                self.server_signals.error_occurred.emit("Impossible de démarrer le serveur")

        except Exception as e:
            print(f"DEBUG: Erreur serveur: {e}")
            self.server_signals.error_occurred.emit(str(e))

    # AJOUT: Méthode pour recevoir les messages du serveur
    def on_message_received(self, message):
        """Callback quand un message est reçu du client"""
        print(f"DEBUG: Message reçu dans Widget: '{message}'")

        # Vérifier que le message n'est pas vide et n'est pas un message système
        if message and not message.startswith("Server:"):
            # Transmettre le message à la page de message si elle existe
            if self.message_page:
                print(f"DEBUG: Transmission du message à MessagePage: '{message}'")
                self.message_page.recevoir_message(message)
            else:
                print("DEBUG: MessagePage non disponible pour afficher le message")
        else:
            print(f"DEBUG: Message système ou vide ignoré: '{message}'")
    def on_client_connected_callback(self, client_address):
        """Callback utilisé par le serveur - émet le signal"""
        self.server_signals.client_connected.emit(str(client_address))

    def on_code_ready(self, code, ip, port):
        """Callback quand le code de connexion est prêt"""
        print(f"DEBUG: on_code_ready appelé avec code: {code}")  # Ajoutez cette ligne

        # Transmet le code à la seconde page
        if self.second_page:
            self.second_page.afficher_code(code, ip, port)
        else:
            print("DEBUG: second_page n'est pas défini")

    def on_client_connected(self, client_address):
        """Callback quand un client se connecte - OUVRE LA PAGE DE MESSAGE"""
        # client_address est un tuple (ip, port), on le formate en string
        if isinstance(client_address, tuple):
            formatted_address = f"{client_address[0]}:{client_address[1]}"
        else:
            formatted_address = str(client_address)

        print(f"DEBUG: Client connecté: {formatted_address}")

        # CORRECTION: Utiliser l'adresse formatée
        self.message_page = MessagePage(self, formatted_address)
        self.message_page.show()

        # Cache la seconde page si elle existe
        if self.second_page:
            self.second_page.hide()

        print("DEBUG: MessagePage créée et affichée")
    def on_server_error(self, error_message):
        """En cas d'erreur du serveur"""
        QMessageBox.critical(self, "Erreur", f"Erreur du serveur:\n{error_message}")

    def rejoindre_salon(self):
        """Quand on clique sur Rejoindre un salon"""
        # Ouvre une page pour saisir le code
        code, ok = QInputDialog.getText(self, "Rejoindre un salon", "Entrez le code de connexion:")
        if ok and code:
            if len(code) == 8:
                try:
                    # Lance le client dans un thread séparé
                    client_thread = threading.Thread(target=self.lancer_client, args=(code,), daemon=True)
                    client_thread.start()

                    # Ouvre la page de chat
                    self.open_chat_page()

                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Impossible de se connecter:\n{e}")
            else:
                QMessageBox.warning(self, "Code invalide", "Le code doit contenir 8 caractères")

    def lancer_client(self, code):
        """Lance le client dans un thread séparé"""
        try:
            start_client(code)  # Ta fonction client existante
        except Exception as e:
            print(f"Erreur client: {e}")

    def open_chat_page(self):
        """Ouvre la page de chat"""
        # À implémenter selon ton UI
        pass

class SecondPage(QWidget):
    def __init__(self, main_page):
        super().__init__()
        self.main_page = main_page
        self.ui = Ui_SecondPage()
        self.ui.setupUi(self)

        self.current_code = ""

        # Connecte le bouton retour - CORRECTION DU NOM DE MÉTHODE
        if hasattr(self.ui, 'btn_retour'):
            self.ui.btn_retour.clicked.connect(self.retour_accueil)  # Changé de btn_retour à retour_accueil

        # Connecte le bouton copier code
        if hasattr(self.ui, 'btn_copier_code'):
            self.ui.btn_copier_code.clicked.connect(self.copier_code)

    def afficher_code(self, code, ip, port):
        """Affiche le code de connexion dans le label"""
        self.current_code = code
        # Méthode 1: Si ton label est accessible via self.ui
        if hasattr(self.ui, 'label_code'):
           print("DEBUG: Label trouvé via self.ui.label_code")  # Debug
           self.ui.label_code.setText(code)
           self.ui.label_code.setStyleSheet("""
               QLabel {
                   background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                               stop:0 #7E57C2, stop:0.5 #BB86FC, stop:1 #7E57C2);
                   color: #FFFFFF;
                   border: 3px solid #BB86FC;
                   border-radius: 15px;
                   padding: 10px;
                   font-size: 28px;
                   font-weight: bold;
                   font-family: 'Courier New', monospace;
                   letter-spacing: 3px;
                   text-align: center;
                   margin: 10px;
               }
           """)
        else:
            # Méthode 2: Si tu as nommé ton label différemment, trouve-le par son nom d'objet
            # Remplace 'label_code' par le nom exact de ton QLabel dans Qt Designer
            label_code = self.findChild(QLabel, 'label_code')
            if label_code:
                label_code.setText(code)
                self.current_code = code
            else:
                print("Erreur: Impossible de trouver le QLabel 'label_code'")

        # Met à jour le statut
        if hasattr(self.ui, 'label_statut'):
            self.ui.label_statut.setText(f" Serveur actif - IP: {ip} Port: {port}")
        else:
            label_statut = self.findChild(QLabel, 'label_statut')
            if label_statut:
                label_statut.setText(f" Serveur actif - IP: {ip} Port: {port}")

    def copier_code(self):
        """Copie le code dans le presse-papier"""
        if self.current_code:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_code)

            # Feedback simple
            self.ui.btn_copier_code.setText("✓ Copié")
            QTimer.singleShot(2000, lambda: self.ui.btn_copier_code.setText("Copier le code"))
    def retour_accueil(self):
        """Retour à la page d'accueil"""
        self.main_page.show()
        self.hide()

        # Arrête le serveur si il est en cours
        if self.main_page.server:
            self.main_page.server.stop_server()

class MessageSignals(QObject):
    """Signaux pour la communication inter-threads"""
    message_received = Signal(str)
    status_changed = Signal(str)


from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame,
                               QHBoxLayout, QScrollArea)
from PySide6.QtCore import Qt, QTimer, Signal, Slot  # <-- Syntaxe PySide6

# Assurez-vous que votre fichier UI a bien été généré avec pyside6-uic
# from ui_message_page import Ui_MessagePage

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt, QTimer, Signal, Slot

class MessagePage(QWidget):
    # --- DÉCLARATION DU SIGNAL (PySide6) ---
    signal_message_recu = Signal(str)

    def __init__(self, main_page, client_address, is_server=True):
        super().__init__()
        self.main_page = main_page
        self.client_address = client_address
        self.is_server = is_server  # True = mode serveur, False = mode client

        # Initialisation de l'UI
        self.ui = Ui_MessagePage()
        self.ui.setupUi(self)

        print(f"DEBUG: Creation MessagePage - Mode: {'Serveur' if is_server else 'Client'}, Adresse: {client_address}")

        # Initialise le système de messages
        self.setup_message_system()

        # --- STYLE SANS BORDURE POUR LE QLINEEDIT ---
        if hasattr(self.ui, 'input_message'):
            self.ui.input_message.setStyleSheet("""
                QLineEdit {
                    background: #1E1E2E;
                    color: #E0E0E0;
                    border: none;
                    border-radius: 15px;
                    padding: 12px 15px;
                    font-size: 14px;
                    selection-background-color: #7E57C2;
                }
                QLineEdit:focus {
                    background: #2A2A3A;
                    border: 2px solid #7E57C2;
                }
            """)

        # --- CONNEXION DU SIGNAL ---
        self.signal_message_recu.connect(self._afficher_message_recu)

        # Affiche le titre approprié selon le mode
        if hasattr(self.ui, 'label_contact'):
            if self.is_server:
                self.ui.label_contact.setText(f"Chat avec {client_address}")
            else:
                self.ui.label_contact.setText("Chat en cours...")

        # Connecte les boutons
        if hasattr(self.ui, 'btn_back'):
            self.ui.btn_back.clicked.connect(self.retour_accueil)
        if hasattr(self.ui, 'btn_send'):
            self.ui.btn_send.clicked.connect(self.envoyer_message)
        if hasattr(self.ui, 'input_message'):
            self.ui.input_message.returnPressed.connect(self.envoyer_message)

        # Message de bienvenue différent selon le mode
        if self.is_server:
            self.afficher_message("", f"✅ Connecté à {client_address}", False)
        else:
            self.afficher_message("", "✅ Connexion établie - Prêt à chatter!", False)

        print("DEBUG: MessagePage initialisee avec succes")

    def setup_message_system(self):
        """Initialise le système de messages avec des widgets individuels"""
        try:
            print("DEBUG: Setup message system")
            if not hasattr(self.ui, 'scroll_messages'):
                print("DEBUG: scroll_messages n'existe pas")
                return

            # Créer un widget conteneur et un layout
            self.messages_container = QWidget()
            self.messages_layout = QVBoxLayout(self.messages_container)
            self.messages_layout.setAlignment(Qt.AlignTop)
            self.messages_layout.setContentsMargins(20, 20, 20, 20)  # Marges augmentées
            self.messages_layout.setSpacing(15)  # Espacement augmenté

            # Configurer la scroll area
            self.ui.scroll_messages.setWidget(self.messages_container)
            self.ui.scroll_messages.setWidgetResizable(True)

            # Style de la scroll area avec la nouvelle couleur #0F0F1A et sans bordures
            self.ui.scroll_messages.setStyleSheet("""
                QScrollArea {
                    background: #0F0F1A;
                    border: none;
                    outline: none;
                }
                QScrollArea QWidget {
                    background: #0F0F1A;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #1A1A2E;
                    width: 12px;
                    margin: 0px;
                    border-radius: 6px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background: #7E57C2;
                    border-radius: 6px;
                    min-height: 20px;
                    border: none;
                }
                QScrollBar::handle:vertical:hover {
                    background: #BB86FC;
                    border: none;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
            """)

            # Appliquer également la couleur au conteneur
            self.messages_container.setStyleSheet("background: #0F0F1A; border: none;")

            print("DEBUG: Setup message system terminé")

        except Exception as e:
            print(f"DEBUG: Erreur setup_message_system: {e}")

    def recevoir_message(self, message):
        """
        Appelé par le thread réseau (socket).
        Ne modifie PAS l'interface directement. Émet juste le signal.
        """
        try:
            print(f"DEBUG: Thread Réseau a reçu: {message}")
            self.signal_message_recu.emit(message)
        except Exception as e:
            print(f"DEBUG: Erreur dans recevoir_message: {e}")

    @Slot(str)
    def _afficher_message_recu(self, message):
        """
        Ce slot s'exécute dans le thread principal (UI).
        C'est ici qu'on peut toucher aux widgets en toute sécurité.
        """
        try:
            print(f"DEBUG: UI Thread affiche: {message}")
            self.afficher_message("", message, False)
        except Exception as e:
            print(f"DEBUG: Erreur _afficher_message_recu: {e}")

    def afficher_message(self, expediteur, message, est_moi=True):
        """Affiche un message avec un widget personnalisé"""
        try:
            # Vérifier que l'UI est toujours disponible
            if not hasattr(self, 'messages_layout'):
                self.setup_message_system()

            if not hasattr(self, 'messages_layout'):
                return

            # Créer le widget de message
            message_widget = self.creer_widget_message(message, est_moi)

            if message_widget:
                self.messages_layout.addWidget(message_widget)
                # Défiler vers le bas (petit délai pour laisser le layout se calculer)
                QTimer.singleShot(100, self.defiler_vers_bas)
            else:
                print("DEBUG: ERREUR - message_widget est None")

        except Exception as e:
            print(f"DEBUG: Erreur afficher_message: {e}")

    def creer_widget_message(self, message, est_moi):
        """Crée un widget de message stylisé avec des blocs BEAUCOUP plus longs - STYLE CORRIGÉ"""
        try:
            container = QWidget()
            # Largeur maximale TRÈS augmentée - 3x plus large
            container.setMaximumWidth(1200)  # Au lieu de 700px
            container.setMinimumHeight(50)

            layout_container = QHBoxLayout(container)
            layout_container.setContentsMargins(15, 8, 15, 8)  # Marges augmentées

            # Frame pour la bulle de message - BEAUCOUP PLUS LONGUE
            frame_message = QFrame()

            # Définir les couleurs selon l'expéditeur
            if est_moi:
                bg_color = "#7E57C2"  # Violet pour mes messages
                border_color = "#BB86FC"
            else:
                bg_color = "#24283B"  # Gris foncé pour les messages reçus
                border_color = "#34354A"

            # STYLE CORRIGÉ - Utilisation de format() au lieu de f-string pour éviter les problèmes
            style_frame = """
                QFrame {{
                    background: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 20px;
                    padding: 15px 20px;
                    min-width: 100px;
                    max-width: 900px;
                }}
            """.format(bg_color=bg_color, border_color=border_color)

            frame_message.setStyleSheet(style_frame)

            # Layout pour le contenu du message
            layout_message = QVBoxLayout(frame_message)
            layout_message.setContentsMargins(0, 0, 0, 0)
            layout_message.setSpacing(6)

            # Message seulement - SUPPRIMÉ l'affichage de l'expéditeur
            label_texte = QLabel(message)
            label_texte.setStyleSheet("""
                color: #E0E0E0;
                font-size: 16px;
                font-weight: normal;
                background: transparent;
                padding: 0px;
                margin: 0px;
                line-height: 1.4;
            """)
            label_texte.setWordWrap(True)
            label_texte.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout_message.addWidget(label_texte)

            # Horodatage
            from datetime import datetime
            label_heure = QLabel(datetime.now().strftime("%H:%M"))
            label_heure.setStyleSheet("color: #A0A0B0; font-size: 12px; font-style: italic;")
            label_heure.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout_message.addWidget(label_heure)

            # Alignement
            if est_moi:
                layout_container.addStretch()
                layout_container.addWidget(frame_message)
            else:
                layout_container.addWidget(frame_message)
                layout_container.addStretch()

            return container

        except Exception as e:
            print(f"DEBUG: Erreur dans creer_widget_message: {e}")
            # Fallback simple
            label = QLabel(f"Message: {message}")
            label.setStyleSheet("color: white; background: red; padding: 10px;")
            return label

    def defiler_vers_bas(self):
        """Fait défiler la zone de messages vers le bas"""
        try:
            if hasattr(self.ui, 'scroll_messages'):
                scrollbar = self.ui.scroll_messages.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            print(f"DEBUG: Erreur defilement: {e}")

    def envoyer_message(self):
        """Envoie le message saisi - GÈRE LES DEUX MODES"""
        try:
            if hasattr(self.ui, 'input_message'):
                message = self.ui.input_message.text().strip()
                if message:
                    print(f"DEBUG: Envoi message (Mode {'Serveur' if self.is_server else 'Client'}): {message}")

                    # 1. Affiche le message localement
                    self.afficher_message("", message, True)

                    # 2. Envoie le message selon le mode
                    if self.is_server:
                        # Mode serveur : envoie via le serveur
                        if hasattr(self.main_page, 'server') and self.main_page.server:
                            success = self.main_page.server.send_message(message)
                            if not success:
                                self.afficher_message("", "❌ Impossible d'envoyer le message", False)
                        else:
                            self.afficher_message("", "❌ Serveur non disponible", False)
                    else:
                        # Mode client : envoie via le client
                        if hasattr(self.main_page, 'client') and self.main_page.client:
                            success = self.main_page.client.send_message(message)
                            if not success:
                                self.afficher_message("", "❌ Impossible d'envoyer le message", False)
                        else:
                            self.afficher_message("", "❌ Client non disponible", False)

                    # 3. Vide le champ
                    self.ui.input_message.clear()

        except Exception as e:
            print(f"DEBUG: Erreur envoi message: {e}")
            self.afficher_message("", f"❌ Erreur: {str(e)}", False)

    def retour_accueil(self):
        """Retour à la page d'accueil"""
        print("DEBUG: Retour accueil")
        self.main_page.show()
        self.hide()

        # Arrête le serveur si on est en mode serveur
        if self.is_server and hasattr(self.main_page, 'server') and self.main_page.server:
            self.main_page.server.stop_server()

        # Arrête le client si on est en mode client
        if not self.is_server and hasattr(self.main_page, 'client') and self.main_page.client:
            self.main_page.client.disconnect()

class SecondPage2(QWidget):
    def __init__(self, main_page):
        super().__init__()
        self.main_page = main_page
        self.ui = Ui_SecondPage2()
        self.ui.setupUi(self)

        # Connecte le bouton retour - CORRECTION DU NOM DE MÉTHODE
        if hasattr(self.ui, 'pushButton'):
            self.ui.pushButton.clicked.connect(self.se_connecter_client)  # Changé de btn_retour à retour_accueil
        if hasattr(self.ui, 'btn_retour'):
            self.ui.btn_retour.clicked.connect(self.retour_accueil)

    def se_connecter_client(self):
            """Quand on clique sur Se connecter avec un code"""
            try:
                if hasattr(self.ui, 'input_code'):
                    code = self.ui.input_code.text().strip()
                    if len(code) == 8:
                        print(f"Tentative de connexion avec le code: {code}")

                        # CORRECTION 1: Stocker message_page dans main_page pour que les messages reçus s'affichent
                        # self.main_page.message_page au lieu de self.message_page
                        self.main_page.message_page = MessagePage(self.main_page, f"Client", is_server=False)
                        self.main_page.message_page.show()
                        self.hide()

                        # Lance le client dans un thread séparé
                        self.client_thread = threading.Thread(target=self.lancer_client, args=(code,), daemon=True)
                        self.client_thread.start()

                    else:
                        QMessageBox.warning(self, "Code invalide", "Le code doit contenir 8 caractères")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur de connexion: {e}")
    def lancer_client(self, code):
            """Lance le client et se connecte"""
            try:
                print("Initialisation du client...")

                # CORRECTION 2: Créer l'instance du client et l'attacher à main_page
                # C'est ce qui permet à MessagePage de trouver 'self.main_page.client'
                self.main_page.client = LANClient()

                # CORRECTION 3: Connecter le callback pour recevoir les messages
                # On réutilise la méthode on_message_received qui existe déjà dans Widget
                self.main_page.client.set_message_callback(self.main_page.on_message_received)

                # Tentative de connexion
                success = self.main_page.client.connect_to_server(code)

                if success:
                    print("Client connecté avec succès !")
                    # Optionnel : Envoyer un message système local
                    # self.main_page.on_message_received("Système: Connecté au serveur !")
                else:
                    print("Échec de la connexion client")
                    # Important : prévenir l'utilisateur si ça échoue (via signal idéalement)

            except Exception as e:
                print(f"Erreur fatale client: {e}")
    def retour_accueil(self):
        """Retour à la page d'accueil"""
        self.main_page.show()
        self.hide()

        # Arrête le serveur si il est en cours
        if self.main_page.server:
            self.main_page.server.stop_server()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
