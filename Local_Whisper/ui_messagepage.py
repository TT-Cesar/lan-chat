# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'messagepage.ui'
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
    QPushButton, QScrollArea, QSizePolicy, QWidget)
import rc_img

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1106, 806)
        self.header = QFrame(Form)
        self.header.setObjectName(u"header")
        self.header.setGeometry(QRect(0, 0, 1091, 81))
        self.header.setStyleSheet(u"background: #16161E;\n"
"    border-bottom: 1px solid #34354A;\n"
"")
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.header.setFrameShadow(QFrame.Shadow.Raised)
        self.btn_back = QPushButton(self.header)
        self.btn_back.setObjectName(u"btn_back")
        self.btn_back.setGeometry(QRect(20, 0, 81, 70))
        self.btn_back.setStyleSheet(u"image: url(:/img/img/icons8-return-64.png);\n"
"background: transparent;\n"
"    border: none;")
        self.label = QLabel(self.header)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(230, 10, 91, 61))
        self.label_contact = QLabel(self.header)
        self.label_contact.setObjectName(u"label_contact")
        self.label_contact.setGeometry(QRect(370, 20, 181, 71))
        self.label_status = QLabel(self.header)
        self.label_status.setObjectName(u"label_status")
        self.label_status.setGeometry(QRect(980, 30, 20, 20))
        self.label_status.setStyleSheet(u"QLabel{\n"
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
"    background-color: #47af40;\n"
"    \n"
"    /* Effet de brillance subtil */\n"
"    border: 1px solid rgba(255, 255, 255, 0.1);\n"
"}\n"
"background-color: rgb(71, 175, 64);")
        self.label_2 = QLabel(self.header)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(870, 0, 58, 71))
        self.footer = QFrame(Form)
        self.footer.setObjectName(u"footer")
        self.footer.setGeometry(QRect(-20, 740, 1091, 82))
        self.footer.setStyleSheet(u"QFrame#footer {\n"
"    background: #1A1B26;\n"
"    border-top: 1px solid #34354A;\n"
"    padding: 10px;\n"
"    min-height: 60px;\n"
"    max-height: 60px;\n"
"}")
        self.footer.setFrameShape(QFrame.Shape.StyledPanel)
        self.footer.setFrameShadow(QFrame.Shadow.Raised)
        self.label_3 = QLabel(self.footer)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(20, 10, 81, 41))
        self.label_3.setPixmap(QPixmap(u":/img/img/Envelope.png"))
        self.input_message = QLineEdit(self.footer)
        self.input_message.setObjectName(u"input_message")
        self.input_message.setGeometry(QRect(110, 10, 841, 51))
        self.input_message.setStyleSheet(u"QLineEdit#input_message {\n"
"    background: #24283B;\n"
"    border: 1px solid #34354A;\n"
"    border-radius: 20px;\n"
"    padding: 8px 15px;\n"
"    color: #E0E0E0;\n"
"    font-size: 14px;\n"
"}")
        self.btn_send = QPushButton(self.footer)
        self.btn_send.setObjectName(u"btn_send")
        self.btn_send.setGeometry(QRect(970, 10, 91, 51))
        self.btn_send.setStyleSheet(u"image: url(:/img/img/Sent.png);\n"
"background: transparent;\n"
"    border: none;\n"
"")
        self.scroll_messages = QScrollArea(Form)
        self.scroll_messages.setObjectName(u"scroll_messages")
        self.scroll_messages.setGeometry(QRect(0, 80, 1071, 661))
        self.scroll_messages.setStyleSheet(u"QScrollArea#scroll_messages {\n"
"    background: #0F0F1A;\n"
"    border: none;\n"
"}\n"
"")
        self.scroll_messages.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 1071, 661))
        self.widget_messages = QWidget(self.scrollAreaWidgetContents)
        self.widget_messages.setObjectName(u"widget_messages")
        self.widget_messages.setGeometry(QRect(0, 10, 1061, 631))
        self.widget_messages.setStyleSheet(u"QWidget#widget_messages {\n"
"    background: #0F0F1A;\n"
"}")
        self.scroll_messages.setWidget(self.scrollAreaWidgetContents)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.btn_back.setText("")
        self.label.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Chat avec :</span></p></body></html>", None))
        self.label_contact.setText(QCoreApplication.translate("Form", u"textlabel", None))
        self.label_status.setText("")
        self.label_2.setText(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Statut</span></p></body></html>", None))
        self.label_3.setText("")
        self.btn_send.setText("")
    # retranslateUi

