# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SecondPage2.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(738, 508)
        self.frame_2 = QFrame(Form)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setGeometry(QRect(0, 100, 731, 401))
        self.frame_2.setStyleSheet(u" QFrame#frame_2 {\n"
"     background: #24283B;\n"
"     border: 1px solid #34354A;\n"
"     border-radius: 14px;\n"
"     padding: 10px;\n"
" }\n"
"\n"
" QFrame#frame_2:hover {\n"
"     background: #2A2D42;\n"
"     border: 1px solid #7E57C2;\n"
" }")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.label = QLabel(self.frame_2)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 20, 211, 41))
        self.input_code = QLineEdit(self.frame_2)
        self.input_code.setObjectName(u"input_code")
        self.input_code.setGeometry(QRect(160, 90, 231, 31))
        self.label_2 = QLabel(self.frame_2)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(30, 210, 211, 41))
        self.pushButton = QPushButton(self.frame_2)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(240, 326, 191, 31))
        self.pushButton.setStyleSheet(u"background-color:#3a295b;\n"
" border-radius: 12px;")
        self.widget = QWidget(Form)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(0, 0, 731, 91))
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
"     /* Forme ronde */\n"
"     min-width: 18px;\n"
"    max-width: 18px;\n"
"    min-height: 18px;\n"
"    max-height: 18px;\n"
"    border-radius: 9px;\n"
"    \n"
"    /* Couleur par d\u00e9faut (d\u00e9connect\u00e9) */\n"
"    background-color: #CF6679;\n"
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

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label.setText(QCoreApplication.translate("Form", u"Saisissez le code de connexion", None))
        self.label_2.setText(QCoreApplication.translate("Form", u" Statut:            Pret \u00e0 se connecter ", None))
        self.pushButton.setText(QCoreApplication.translate("Form", u"Commencer \u00e0 discuter", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt;\">Creation du salon</span></p></body></html>", None))
        self.label_7.setText(QCoreApplication.translate("Form", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt; font-weight:700;\">Statut</span></p></body></html>", None))
        self.label_8.setText("")
        self.btn_retour.setText("")
    # retranslateUi

