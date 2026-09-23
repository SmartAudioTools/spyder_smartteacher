# -*- coding: utf-8 -*-
"""Le widget du dock : le panneau du TP, et deux actions, « Ouvrir un sujet… » et « Choisir mon fichier… ».

Il cree le pont a la premiere ouverture (un seul pour la seance de Spyder) et la Seance qui relie le paquet a
l'editeur ; le greffon lui donne ``editeur`` (plugin.EditeurSpyder). Les dialogues sont des methodes, remplacees
dans les tests.
"""

import os

import qtawesome as qta
from qtpy.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox, QVBoxLayout

from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.utils.icon_manager import ima

from spyder_smartteacher.client import Pont, PontErreur
from spyder_smartteacher.seance import Seance
from spyder_smartteacher.spyder.widgets.panneau import PanneauTP

OUVRIR, LIER = "smartteacher_ouvrir", "smartteacher_lier"


class SmartTeacherWidget(PluginMainWidget):
    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)
        self.editeur = None  # pose par le greffon quand l'editeur de Spyder est pret
        self.environ, self.fabrique_pont = os.environ, Pont
        self.pont = self.seance = None
        self.panneau = PanneauTP(self)
        disposition = QVBoxLayout()
        disposition.addWidget(self.panneau)
        self.setLayout(disposition)

    def get_title(self):
        return "SmartTeacher"

    def setup(self):
        for nom, texte, icone, action in (
                (OUVRIR, "Ouvrir un sujet…", "mdi.folder-open-outline", self.ouvrir_sujet),
                (LIER, "Choisir mon fichier…", "mdi.link-variant", self.choisir_fichier)):
            # triggered passe l'etat coche (False) : ``paquet or dialogue`` ouvre alors le dialogue.
            self.add_item_to_toolbar(self.create_action(nom, text=texte, icon=qta.icon(icone, color=ima.MAIN_FG_COLOR),
                                                        triggered=action),
                                     toolbar=self.get_main_toolbar())

    def update_actions(self):
        self.get_action(LIER).setEnabled(self.panneau.session is not None)

    def on_close(self):
        if self.pont is not None:
            self.pont.fermer()

    # -- dialogues (remplaces dans les tests)

    def avertir(self, texte):
        QMessageBox.warning(self, "SmartTeacher", texte)

    def demander_mot_de_passe(self, erreur):
        texte, ok = QInputDialog.getText(self, "SmartTeacher", f"Sujet protégé ({erreur}). Mot de passe :",
                                         QLineEdit.Password)
        return texte if ok else None

    def demander_eleve(self):
        nom, ok = QInputDialog.getText(self, "SmartTeacher", "Ton nom de famille :")
        if not (ok and nom.strip()):
            return None
        prenom, ok = QInputDialog.getText(self, "SmartTeacher", "Ton prénom :")
        return (nom, prenom) if ok and prenom.strip() else None

    # -- actions

    def ouvrir_sujet(self, paquet=None):
        paquet = paquet or QFileDialog.getOpenFileName(self, "Ouvrir un sujet", "", "Sujets (*.qcm)")[0]
        if not paquet:
            return
        try:
            if self.pont is None:
                self.pont = self.fabrique_pont()
            seance = Seance(self.pont, self.editeur, self.demander_mot_de_passe, self.demander_eleve, self.environ)
            ouvert = seance.ouvrir(paquet)
        except (OSError, PontErreur) as erreur:
            self.avertir(f"Impossible d'ouvrir le sujet : {erreur}")
            return
        if ouvert is None:
            return
        self.seance = seance
        self.panneau.photo = lambda: seance.photo(self.panneau.confirmer)
        self.panneau.apres_action = seance.sauver
        self.panneau.charger(*ouvert)
        self.update_actions()

    def choisir_fichier(self, chemin=None):
        chemin = chemin or QFileDialog.getOpenFileName(self, "Choisir mon fichier", "", "Python (*.py)")[0]
        if chemin:
            self.seance.lier(str(chemin))

    def renomme(self, ancien, nouveau):
        if self.seance is not None:
            self.seance.renomme(ancien, nouveau)
