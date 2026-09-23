# -*- coding: utf-8 -*-
"""Greffon « SmartTeacher » : le sujet d'un TP dans un dock, l'eleve code dans l'editeur de Spyder.

Seule couche qui connait le plugin Editor : EditeurSpyder lui traduit les trois gestes dont la Seance a besoin
(ouvrir un fichier, lire l'onglet actif, l'enregistrer) et lui signale les « Enregistrer sous ».
"""

import qtawesome as qta

from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.utils.icon_manager import ima

from spyder_smartteacher.spyder.widgets.main_widget import SmartTeacherWidget


class EditeurSpyder:
    """``renomme(ancien, nouveau)`` est appele a chaque « Enregistrer sous ».

    Spyder n'a pas de signal public pour cela : chaque pile d'onglets (EditorStack) emet ``file_renamed_in_data``,
    et une vue scindee cree des piles neuves ; elles sont branchees des qu'un fichier s'y ouvre ou s'y active."""

    def __init__(self, editeur, renomme):
        self.editeur, self.renomme, self.branchees = editeur, renomme, set()
        editeur.sig_file_opened_closed_or_updated.connect(self._brancher)
        self._brancher()

    def _brancher(self, *_):
        for pile in self.editeur.get_widget().editorstacks:
            if id(pile) not in self.branchees:
                self.branchees.add(id(pile))
                pile.file_renamed_in_data.connect(lambda ancien, nouveau, _pile: self.renomme(ancien, nouveau))

    def ouvrir(self, chemin):
        self.editeur.load(filenames=chemin)

    def fichier_actif(self):
        return self.editeur.get_current_filename()

    def enregistrer_actif(self):
        self.editeur.save()  # l'onglet actif : save() ignore son argument index (Spyder 6.1)


class SmartTeacher(SpyderDockablePlugin):
    NAME = "smartteacher"  # doit etre identique au nom du point d'entree
    REQUIRES = [Plugins.Editor]
    WIDGET_CLASS = SmartTeacherWidget
    CONF_SECTION = "smartteacher"
    CONF_FILE = False

    @staticmethod
    def get_name():
        return "SmartTeacher"

    @staticmethod
    def get_description():
        return "Sujet de TP : énoncé, aide, indices, soumission et note de chaque étape."

    @classmethod
    def get_icon(cls):
        return qta.icon("mdi.school-outline", color=ima.MAIN_FG_COLOR)

    def on_initialize(self):
        pass  # obligatoire (NotImplementedError sinon) ; tout se branche quand l'editeur est pret

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        widget.editeur = EditeurSpyder(self.get_plugin(Plugins.Editor), widget.renomme)
