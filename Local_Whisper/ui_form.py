# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
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

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(766, 685)
        Widget.setStyleSheet(u"\n"
"    background: #0F0F1A;\n"
"    border: none;")
        self.widget = QWidget(Widget)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(0, 0, 761, 131))
        self.widget.setStyleSheet(u"QWidget {\n"
"    background: #16161E;\n"
"    border-bottom: 1px solid #34354A;\n"
"   \n"
"}")
        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(190, 60, 131, 61))
        self.label.setStyleSheet(u"QLabel {\n"
"    color: #E0E0E0;\n"
"    font-size: 18px;\n"
"    font-weight: bold;\n"
"}")
        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(540, 60, 81, 61))
        self.label_2.setStyleSheet(u"QLabel {\n"
"    color: #E0E0E0;\n"
"    font-size: 18px;\n"
"    font-weight: bold;\n"
"}")
        self.label_12 = QLabel(self.widget)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setGeometry(QRect(660, 80, 20, 20))
        self.label_12.setStyleSheet(u"QLabel{\n"
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
        self.label_11 = QLabel(self.widget)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setGeometry(QRect(20, 0, 151, 121))
        self.label_11.setStyleSheet(u"image: url(:/img/img/LocalWhisper_Logo_Violet.png);")
        self.label_11.setPixmap(QPixmap(u":/img/img/logo.svg"))
        self.widget_5 = QWidget(Widget)
        self.widget_5.setObjectName(u"widget_5")
        self.widget_5.setGeometry(QRect(20, 570, 741, 101))
        self.widget_5.setStyleSheet(u"background: #16161E;\n"
"border-top: 1px solid #34354A;")
        self.label_10 = QLabel(self.widget_5)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setGeometry(QRect(100, 10, 271, 81))
        self.label_10.setStyleSheet(u"color: rgb(255, 255, 255);")
        self.card = QFrame(Widget)
        self.card.setObjectName(u"card")
        self.card.setGeometry(QRect(40, 180, 311, 371))
        self.card.setStyleSheet(u" QFrame#card {\n"
"     background: #24283B;\n"
"     border: 1px solid #34354A;\n"
"     border-radius: 14px;\n"
"     padding: 10px;\n"
" }\n"
"\n"
" QFrame#card:hover {\n"
"     background: #2A2D42;\n"
"     border: 1px solid #7E57C2;\n"
" }")
        self.card.setFrameShape(QFrame.Shape.StyledPanel)
        self.card.setFrameShadow(QFrame.Shadow.Raised)
        self.pushButton = QPushButton(self.card)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(50, 290, 201, 27))
        self.pushButton.setStyleSheet(u"background-color:#7E57C2;\n"
" border-radius: 12px;")
        self.label_7 = QLabel(self.card)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setGeometry(QRect(120, 50, 91, 91))
        self.label_7.setStyleSheet(u" background: transparent;\n"
"    border: none;")
        self.label_7.setPixmap(QPixmap(u":/img/img/server.png"))
        self.label_3 = QLabel(self.card)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 160, 291, 101))
        self.label_3.setStyleSheet(u" background: transparent;\n"
"    border: none;\n"
"\n"
" QLabel#label_3:hover {\n"
"     background: #2A2D42;\n"
"     border: 1px solid #7E57C2;\n"
" }")
        self.card1 = QFrame(Widget)
        self.card1.setObjectName(u"card1")
        self.card1.setGeometry(QRect(400, 180, 311, 371))
        self.card1.setStyleSheet(u" QFrame#card1 {\n"
"     background: #24283B;\n"
"     border: 1px solid #34354A;\n"
"     border-radius: 14px;\n"
"     padding: 10px;\n"
" }\n"
"\n"
" QFrame#card1:hover {\n"
"     background: #2A2D42;\n"
"     border: 1px solid #7E57C2;\n"
" }")
        self.card1.setFrameShape(QFrame.Shape.StyledPanel)
        self.card1.setFrameShadow(QFrame.Shadow.Raised)
        self.pushButton_2 = QPushButton(self.card1)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setGeometry(QRect(50, 290, 201, 27))
        self.pushButton_2.setStyleSheet(u"background-color:#7E57C2;\n"
" border-radius: 12px;")
        self.label_5 = QLabel(self.card1)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 150, 271, 121))
        self.label_5.setStyleSheet(u" background: transparent;\n"
"    border: none;")
        self.label_8 = QLabel(self.card1)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setGeometry(QRect(120, 70, 81, 61))
        self.label_8.setStyleSheet(u" background: transparent;\n"
"    border: none;")
        self.label_8.setPixmap(QPixmap(u":/img/img/client.png"))

        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Widget", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Local Whisper", None))
        self.label_2.setText(QCoreApplication.translate("Widget", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:18px; font-weight:700; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:14pt;\">Statut </span></p></body></html>", None))
        self.label_12.setText("")
        self.label_11.setText("")
        self.label_10.setText(QCoreApplication.translate("Widget", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Comment \u00e7a marche?</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">1. Cr\u00e9ez un salon et partagez le code</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">2 .Rejoignez avec un code re\u00e7cu</p>\n"
"<p style=\" margin-top:0px; margin"
                        "-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">3. Disctutez Instantan\u00e9ment </p></body></html>", None))
        self.pushButton.setText(QCoreApplication.translate("Widget", u"Creer le Salon", None))
        self.label_7.setText("")
        self.label_3.setText(QCoreApplication.translate("Widget", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Creer un Salon</span></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">je veux que quelqu'un me rejoigne</span></p></body></html>", None))
        self.pushButton_2.setText(QCoreApplication.translate("Widget", u"Rejoindre un Salon", None))
        self.label_5.setText(QCoreApplication.translate("Widget", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Rejoindre un salon</span></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">je veux me connecter \u00e0 quelqu'un</span></p></body></html>", None))
        self.label_8.setText("")
    # retranslateUi

