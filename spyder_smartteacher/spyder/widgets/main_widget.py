# -*- coding: utf-8 -*-
"""Le widget du dock : le panneau du TP, et dans sa barre d'outils les deux triangles de navigation du panneau.

Un sujet s'ouvre par Fichier > Ouvrir de Spyder (le greffon declare l'extension .qcm, voir plugin.py) : ni bouton
propre, ni menu d'options.

Retenus dans la configuration de Spyder (section « smartteacher » de spyder.ini) : le dernier sujet ouvert, rouvert
au lancement suivant comme l'editeur rouvre ses fichiers, et le nom de l'eleve s'il a fallu le demander.

Il cree le pont a la premiere ouverture (un seul pour la seance de Spyder) et la Seance qui relie le paquet a
l'editeur ; le greffon lui donne ``editeur`` (plugin.EditeurSpyder). Les dialogues sont des methodes, remplacees
dans les tests.
"""

import os
from pathlib import Path

import qtawesome as qta
from qtpy.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QVBoxLayout

from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.utils.icon_manager import ima

from spyder_smartteacher.client import Pont, PontErreur
from spyder_smartteacher.seance import Seance
from spyder_smartteacher.spyder.widgets.panneau import PanneauTP

PRECEDENT, SUIVANT = "smartteacher_precedent", "smartteacher_suivant"


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
        for action, nom, icone in ((self.panneau.precedent, PRECEDENT, "mdi.arrow-left-drop-circle-outline"),
                                   (self.panneau.suivant, SUIVANT, "mdi.arrow-right-drop-circle-outline")):
            action.action_id = nom  # identifiant exige par la barre d'outils de Spyder
            action.setIcon(qta.icon(icone, color=ima.MAIN_FG_COLOR))
            self.add_item_to_toolbar(action, toolbar=self.get_main_toolbar())
        # Le menu d'options est vide : on retire son bouton. Il vit dans la barre de coin, ou c'est l'action qui le
        # porte qui decide de sa visibilite (le setVisible du fork SmartOS sur le bouton lui-meme n'y tient pas).
        coin = self._corner_widget
        for action in coin.actions():
            if coin.widgetForAction(action) is self._options_button:
                action.setVisible(False)

    def update_actions(self):
        pass  # obligatoire ; les triangles sont tenus a jour par le panneau

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

    def eleve_retenu(self):
        """Sans ELEVE_NOM / ELEVE_PRENOM (poste personnel) : le nom donne une fois, retenu dans spyder.ini."""
        eleve = tuple(self.get_conf("eleve", default=[])) or self.demander_eleve()
        if eleve:
            self.set_conf("eleve", list(eleve))
        return eleve

    # -- actions

    def ouvrir_sujet(self, paquet):
        try:
            if self.pont is None:
                self.pont = self.fabrique_pont()
            seance = Seance(self.pont, self.editeur, self.demander_mot_de_passe, self.eleve_retenu, self.environ)
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
        self.set_conf("dernier_sujet", str(paquet))

    def rouvrir_dernier(self):
        """Au lancement de Spyder : le dernier sujet ouvert, s'il existe encore (mot de passe redemande)."""
        paquet = self.get_conf("dernier_sujet", default="")
        if paquet and Path(paquet).is_file():
            self.ouvrir_sujet(paquet)

    def renomme(self, ancien, nouveau):
        if self.seance is not None:
            self.seance.renomme(ancien, nouveau)
