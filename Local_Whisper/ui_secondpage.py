# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'secondpage.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QPushButton,
    QSizePolicy, QWidget)
import rc_img

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(772, 667)
        Form.setStyleSheet(u"background-color: rgb(0, 0, 0);")
        self.widget = QWidget(Form)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(30, 30, 731, 91))
        self.widget.setStyleSheet(u"QWidget {\n"
"    background: #16161E;\n"
"    border-bottom: 1px solid #34354A;\n"
"   \n"
"}")
        self.label_6 = QLabel(self.widget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(220, 50, 171, 21))
        self.label_6.setStyleSheet(u"")
        self.label_7 = QLabel(self.widget)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setGeometry(QRect(510, 50, 61, 31))
        self.label_8 = QLabel(self.widget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(650, 50, 20, 20))
        self.label_8.setStyleSheet(u"QLabel{\n"
"	background-color: rgb(208, 160, 64);\n"
"     /* Forme ronde */\n"
"     min-width: 18px;\n"
"    max-width: 18px;\n"
"    min-height: 18px;\n"
"    max-height: 18px;\n"
"    border-radius: 9px;\n"
"	color: rgb(255, 175, 94);\n"
"    \n"
"    /* Couleur par d\u00e9faut (d\u00e9connect\u00e9) */\n"
"    background-color: #d0a040;\n"
"    \n"
"    /* Effet de brillance subtil */\n"
"    border: 1px solid rgba(255, 255, 255, 0.1);\n"
"}\n"
"")
        self.btn_retour = QPushButton(self.widget)
        self.btn_retour.setObjectName(u"btn_retour")
        self.btn_retour.setGeometry(QRect(20, 20, 81, 51))
        self.btn_retour.setStyleSheet(u"image: url(:/img/img/icons8-return-64.png);\n"
"background: transparent;\n"
"    border: none;")
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setGeometry(QRect(30, 140, 721, 521))
        self.frame.setStyleSheet(u" QFrame#frame {\n"
"     background: #24283B;\n"
"     border: 1px solid #34354A;\n"
"     border-radius: 14px;\n"
"     padding: 10px;\n"
" }\n"
"\n"
" QFrame#frame:hover {\n"
"     background: #2A2D42;\n"
"     border: 1px solid #7E57C2;\n"
" }")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.btn_copier_code = QPushButton(self.frame)
        self.btn_copier_code.setObjectName(u"btn_copier_code")
        self.btn_copier_code.setGeometry(QRect(240, 300, 231, 31))
        self.btn_copier_code.setStyleSheet(u"background-color:#7E57C2;\n"
" border-radius: 12px;")
        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(240, 20, 241, 31))
        self.label_2.setStyleSheet(u"background: transparent;\n"
"    border: none;")
        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(60, 410, 321, 71))
        self.label_5.setStyleSheet(u"background: transparent;\n"
"    border: none;")
        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(80, 130, 181, 31))
        self.label_4.setStyleSheet(u"background: transparent;\n"
"    border: none;\n"
"")
        self.pushButton_2 = QPushButton(self.frame)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setGeometry(QRect(240, 370, 231, 31))
        self.pushButton_2.setStyleSheet(u"background-color:#7E57C2;\n"
" border-radius: 12px;")
        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(80, 60, 261, 41))
        self.label_3.setStyleSheet(u"background: transparent;\n"
"    border: none;")
        self.label_code = QLabel(self.frame)
        self.label_code.setObjectName(u"label_code")
        self.label_code.setGeometry(QRect(230, 170, 251, 81))
        self.label_code.setStyleSheet(u"background: transparent;\n"
"    border: none;")
        self.pushButton_3 = QPushButton(self.frame)
        self.pushButton_3.setObjectName(u"pushButton_3")
        self.pushButton_3.setGeometry(QRect(40, 480, 231, 31))
        self.pushButton_3.setStyleSheet(u"background-color:#7E57C2;\n"
" border-radius: 12px;")
        self.label_9 = QLabel(self.frame)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setGeometry(QRect(320, 420, 61, 61))
        self.label_9.setStyleSheet(u"background: transparent;\n"
"    border: none;")
        self.label_9.setPixmap(QPixmap(u":/img/img/icons8-iphone-spinner-64.png"))

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt;\">Creation du salon</span></p></body></html>", None))
        self.label_7.setText(QCoreApplication.translate("Form", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">Statut</span></p></body></html>", None))
        self.label_8.setText("")
        self.btn_retour.setText("")
        self.btn_copier_code.setText(QCoreApplication.translate("Form", u"Copier le code", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:700; color:#7e57c2;\">Salon cr\u00e9\u00e9 avec succes</span></p></body></html>", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:12pt;\">Statut:  En attente de connexion </span></p></body></html>", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:12pt;\">Partager le code</span></p></body></html>", None))
        self.pushButton_2.setText(QCoreApplication.translate("Form", u"Generer un QRcode", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:12pt;\">En attente de connexion...</span></p></body></html>", None))
        self.label_code.setText(QCoreApplication.translate("Form", u"<html><head/><body><p>Creation  du code...</p></body></html>", None))
        self.pushButton_3.setText(QCoreApplication.translate("Form", u"Annuler", None))
        self.label_9.setText("")
    # retranslateUi

