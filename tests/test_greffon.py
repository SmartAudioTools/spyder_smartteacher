"""Le greffon Spyder : le dock construit comme Spyder le fait, l'adaptateur de l'editeur, l'ouverture d'un sujet.

Tourne dans le venv de Spyder, avec une configuration de Spyder jetable (SPYDER_CONFDIR) : jamais celle du compte.
Le pont et l'editeur sont les factices de test_seance ; le vrai pont est teste dans test_pont.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

CONFIG = tempfile.mkdtemp(prefix="spyder-conf-")
os.environ["SPYDER_CONFDIR"] = CONFIG  # avant tout import de spyder

try:
    import spyder  # noqa: F401
except ImportError:
    spyder = None

from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QApplication

from spyder_smartteacher.client import PontErreur
from spyder_smartteacher.tp import SOUMISE
from tests.test_seance import ENV, NOM, EditeurFactice, PontFactice

app = QApplication.instance() or QApplication([])


def tearDownModule():
    shutil.rmtree(CONFIG, ignore_errors=True)


def construire():
    """Le widget du dock, par la sequence d'appels de Spyder (new_api.py : __init__, _setup, setup, update_actions,
    render_toolbars)."""
    from spyder_smartteacher.spyder.plugin import SmartTeacher
    classe = type("Essai", (SmartTeacher.WIDGET_CLASS,),
                  {"CONF_SECTION": SmartTeacher.CONF_SECTION, "PLUGIN_NAME": SmartTeacher.NAME})
    widget = classe(name=SmartTeacher.NAME, plugin=None, parent=None)
    widget._setup()
    widget.setup()
    widget.update_actions()
    widget.render_toolbars()
    return widget


@unittest.skipIf(spyder is None, "Spyder absent de ce Python")
class Greffon(unittest.TestCase):
    def test_declaration(self):
        import tomllib
        from spyder_smartteacher.spyder.plugin import SmartTeacher
        pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
        self.assertIn(SmartTeacher.NAME, pyproject["project"]["entry-points"]["spyder.plugins"])
        self.assertFalse(SmartTeacher.get_icon().isNull())
        self.assertTrue(SmartTeacher.get_name() and SmartTeacher.get_description())
        # Un crochet on_plugin_available sur un greffon non declare leve une SpyderAPIError avalee au demarrage.
        surveilles = {getattr(getattr(SmartTeacher, n), "_plugin_listen", None) for n in dir(SmartTeacher)} - {None}
        self.assertTrue(surveilles <= set(SmartTeacher.REQUIRES) | set(SmartTeacher.OPTIONAL), surveilles)

    def test_construction(self):
        w = construire()
        self.assertTrue(w.get_title())
        self.assertIsNotNone(w.panneau)
        self.assertEqual({"smartteacher_ouvrir", "smartteacher_lier"} - set(w.get_actions()), set())
        self.assertFalse(w.get_action("smartteacher_lier").isEnabled())  # pas de sujet ouvert


class StackFactice(QObject):
    file_renamed_in_data = Signal(str, str, str)


class EditeurSpyderFactice(QObject):
    """Ce que l'adaptateur utilise du plugin Editor de Spyder."""
    sig_file_opened_closed_or_updated = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.stacks, self.charges, self.courant, self.sauvegardes = [StackFactice()], [], None, 0
        self.widget = type("W", (), {"editorstacks": self.stacks})()

    def get_widget(self):
        return self.widget

    def load(self, filenames=None):
        self.charges.append(filenames)
        self.courant = filenames

    def get_current_filename(self):
        return self.courant

    def save(self):
        self.sauvegardes += 1


@unittest.skipIf(spyder is None, "Spyder absent de ce Python")
class Adaptateur(unittest.TestCase):
    def setUp(self):
        from spyder_smartteacher.spyder.plugin import EditeurSpyder
        self.spyder, self.renommages = EditeurSpyderFactice(), []
        self.e = EditeurSpyder(self.spyder, lambda ancien, nouveau: self.renommages.append((ancien, nouveau)))

    def test_trois_gestes(self):
        self.e.ouvrir("/x/a.py")
        self.assertEqual(self.spyder.charges, ["/x/a.py"])
        self.assertEqual(self.e.fichier_actif(), "/x/a.py")
        self.e.enregistrer_actif()
        self.assertEqual(self.spyder.sauvegardes, 1)

    def test_renommage_suivi_dans_toutes_les_piles(self):
        self.spyder.stacks[0].file_renamed_in_data.emit("/x/a.py", "/x/b.py", "1")
        self.spyder.stacks.append(StackFactice())  # vue scindee : une pile neuve
        self.spyder.sig_file_opened_closed_or_updated.emit("/x/b.py", "python")
        self.spyder.sig_file_opened_closed_or_updated.emit("/x/b.py", "python")  # pas de double branchement
        self.spyder.stacks[1].file_renamed_in_data.emit("/x/b.py", "/x/c.py", "2")
        self.spyder.stacks[0].file_renamed_in_data.emit("/x/c.py", "/x/d.py", "1")
        self.assertEqual(self.renommages, [("/x/a.py", "/x/b.py"), ("/x/b.py", "/x/c.py"), ("/x/c.py", "/x/d.py")])


@unittest.skipIf(spyder is None, "Spyder absent de ce Python")
class OuvrirUnSujet(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dossier)
        self.paquet = self.dossier / "pyxel_projet_monkey.qcm"
        self.pont, self.avertissements = PontFactice(), []
        self.w = construire()
        self.w.editeur = EditeurFactice()
        self.w.environ = ENV
        self.w.fabrique_pont = lambda: self.pont
        self.w.demander_mot_de_passe = lambda erreur: "secret"
        self.w.avertir = self.avertissements.append
        self.w.panneau.confirmer = lambda question: True

    def test_ouvrir_puis_soumettre(self):
        self.w.ouvrir_sujet(self.paquet)
        self.assertEqual(self.w.editeur.ouverts, [str(self.dossier / NOM)])
        self.assertTrue(self.w.get_action("smartteacher_lier").isEnabled())
        (self.dossier / NOM).write_text("juste")
        self.w.panneau.bouton_soumettre.click()
        self.assertEqual(self.pont.corriger.appels, [("e1", "juste")])
        journal = self.pont.journaux[str(self.dossier / "LEFÈVRE_Zoé_TP_pyxel-projet-monkey.journal")]
        self.assertEqual(journal["etapes"]["e1"]["statut"], SOUMISE)  # apres_action a enregistre le journal

    def test_choisir_mon_fichier(self):
        self.w.ouvrir_sujet(self.paquet)
        autre = self.dossier / "monkey.py"
        autre.write_text("x")
        self.w.choisir_fichier(autre)
        self.assertEqual(self.w.seance.session.fichier, str(autre))
        self.assertEqual(self.w.editeur.actif, str(autre))

    def test_renonce_au_mot_de_passe(self):
        self.w.demander_mot_de_passe = lambda erreur: None
        self.w.ouvrir_sujet(self.paquet)
        self.assertIsNone(self.w.panneau.session)
        self.assertEqual(self.avertissements, [])

    def test_erreur_du_pont_affichee(self):
        def panne():
            raise OSError("python du QCM introuvable")
        self.w.fabrique_pont = panne
        self.w.ouvrir_sujet(self.paquet)
        self.assertIn("introuvable", self.avertissements[0])

        self.w.fabrique_pont = lambda: self.pont
        def illisible(paquet, mot_de_passe=None):
            raise PontErreur("paquet illisible")
        self.pont.ouvrir = illisible
        self.w.ouvrir_sujet(self.paquet)
        self.assertIn("illisible", self.avertissements[1])

    def test_l_action_ouvre_le_dialogue(self):
        from unittest import mock
        with mock.patch("spyder_smartteacher.spyder.widgets.main_widget.QFileDialog.getOpenFileName",
                        return_value=(str(self.paquet), "")) as dialogue:
            self.w.get_action("smartteacher_ouvrir").trigger()
        dialogue.assert_called_once()
        self.assertIsNotNone(self.w.panneau.session)

    def test_un_seul_pont_pour_plusieurs_sujets(self):
        crees = []
        self.w.fabrique_pont = lambda: crees.append(1) or self.pont
        self.w.ouvrir_sujet(self.paquet)
        self.w.ouvrir_sujet(self.paquet)
        self.assertEqual(crees, [1])


if __name__ == "__main__":
    unittest.main()
