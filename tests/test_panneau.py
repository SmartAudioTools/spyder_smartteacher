"""Le panneau du dock : l'affichage d'une Session, sans Spyder ni pont (correcteur factice, offscreen).

Le greffon lui fournit deux fonctions : ``photo()`` (enregistre le fichier de l'eleve dans l'editeur et en rend le
texte lu sur le disque, ou None si l'eleve renonce) et ``apres_action()`` (enregistre le journal).
"""

import unittest

from qtpy.QtWidgets import QApplication

from spyder_smartteacher.spyder.widgets.panneau import PanneauTP
from spyder_smartteacher.tp import A_FAIRE, CORRIGEE, SOUMISE, TRAITEE, Session
from tests.test_session import Correcteur, Horloge, etapes

app = QApplication.instance() or QApplication([])


class Base(unittest.TestCase):
    def setUp(self):
        self.horloge, self.correcteur = Horloge(), Correcteur()
        self.session = Session(etapes(), correcteur=self.correcteur, horloge=self.horloge)
        self.texte, self.sauvegardes = "juste", []
        self.p = PanneauTP()
        self.p.photo = lambda: self.texte
        self.p.apres_action = lambda: self.sauvegardes.append(1)
        self.p.confirmer = lambda question: True
        self.p.charger(self.session, "Créer un jeu")

    def ligne(self, i):
        return self.p.liste.item(i).text()


class Affichage(Base):
    def test_etapes_listees_et_premiere_ouverte(self):
        self.assertEqual(self.p.liste.count(), 3)
        self.assertEqual(self.p.liste.currentRow(), 0)
        self.assertIn("Etape 1", self.p.enonce.toPlainText())
        self.assertIsNotNone(self.session.journal["etapes"]["e1"]["ouverte"])
        self.assertIsNone(self.session.journal["etapes"]["e2"]["ouverte"])
        self.assertIn(A_FAIRE, self.ligne(0))
        self.assertIn("0 / 4", self.p.total.text())

    def test_changer_d_etape(self):
        self.p.liste.setCurrentRow(1)
        self.assertIn("Etape 2", self.p.enonce.toPlainText())
        self.assertIsNotNone(self.session.journal["etapes"]["e2"]["ouverte"])
        self.assertFalse(self.p.bouton_aide.isEnabled())  # pas d'aide pour l'etape 2


class AideEtIndices(Base):
    def test_aide(self):
        self.p.bouton_aide.click()
        self.assertIn("partie « blt »", self.p.retour.toPlainText())
        self.assertTrue(self.session.journal["etapes"]["e1"]["aidee"])
        self.assertEqual(self.sauvegardes, [1])

    def test_indice_attend_son_delai(self):
        self.assertFalse(self.p.bouton_indice.isEnabled())
        self.assertIn("60 s", self.p.bouton_indice.text())
        self.horloge.t += 60
        self.p.rafraichir()
        self.assertTrue(self.p.bouton_indice.isEnabled())
        self.p.bouton_indice.click()
        self.assertIn("regarde la ligne 3", self.p.retour.toPlainText())
        self.assertIn("60 s", self.p.bouton_indice.text())  # le second attend encore

    def test_indices_vus_restent_affiches(self):
        self.horloge.t += 60
        self.p.rafraichir()
        self.p.bouton_indice.click()
        self.p.liste.setCurrentRow(1)
        self.p.liste.setCurrentRow(0)
        self.assertIn("regarde la ligne 3", self.p.retour.toPlainText())


class Soumettre(Base):
    def test_soumission_notee_et_gelee(self):
        self.p.bouton_soumettre.click()
        self.assertEqual(self.session.statut(0), SOUMISE)
        self.assertEqual(self.correcteur.appels, [("e1", "juste")])
        self.assertIn("2 / 2", self.ligne(0))
        self.assertIn("corrige e1", self.p.retour.toPlainText())
        self.assertIn("2 / 4", self.p.total.text())
        self.assertFalse(self.p.bouton_soumettre.isEnabled())
        self.assertFalse(self.p.bouton_marquer.isEnabled())
        self.assertEqual(self.sauvegardes, [1])

    def test_confirmation_refusee(self):
        self.p.confirmer = lambda question: False
        self.p.bouton_soumettre.click()
        self.assertEqual(self.session.statut(0), A_FAIRE)

    def test_l_eleve_renonce_a_la_photo(self):
        self.texte = None
        self.p.bouton_soumettre.click()
        self.assertEqual(self.session.statut(0), A_FAIRE)
        self.assertEqual(self.sauvegardes, [])

    def test_erreur_de_correction_affichee(self):
        def panne(id, texte):
            raise RuntimeError("le pont s'est arrêté")
        self.session.correcteur = panne
        self.p.bouton_soumettre.click()
        self.assertIn("le pont s'est arrêté", self.p.retour.toPlainText())


class Marquer(Base):
    def test_marquer_sans_note(self):
        self.p.bouton_marquer.click()
        self.assertEqual(self.session.statut(0), TRAITEE)
        self.assertIn(TRAITEE, self.ligne(0))
        self.assertEqual(self.correcteur.appels, [])
        self.assertTrue(self.p.bouton_soumettre.isEnabled())
        self.assertEqual(self.sauvegardes, [1])


class Terminer(Base):
    def test_terminer(self):
        self.p.bouton_soumettre.click()
        self.p.liste.setCurrentRow(1)
        self.texte = "moitie"
        self.p.bouton_marquer.click()
        self.texte = "final"
        self.p.bouton_terminer.click()
        self.assertTrue(self.session.fini)
        self.assertEqual([self.session.statut(i) for i in range(3)], [SOUMISE, CORRIGEE, CORRIGEE])
        self.assertIn("2.5 / 4", self.p.total.text())
        for bouton in (self.p.bouton_soumettre, self.p.bouton_marquer, self.p.bouton_terminer, self.p.bouton_indice):
            self.assertFalse(bouton.isEnabled())
        self.p.liste.setCurrentRow(2)
        self.assertIn("fichier final", self.p.retour.toPlainText())  # le repli se dit

    def test_terminer_demande_confirmation(self):
        self.p.confirmer = lambda question: False
        self.p.bouton_terminer.click()
        self.assertFalse(self.session.fini)


class Reprise(Base):
    def test_reprise_d_une_session_finie(self):
        self.p.bouton_terminer.click()
        p = PanneauTP()
        p.charger(Session(etapes(), journal=self.session.journal, correcteur=self.correcteur), "Créer un jeu")
        self.assertFalse(p.bouton_terminer.isEnabled())
        self.assertIn(CORRIGEE, p.liste.item(0).text())


if __name__ == "__main__":
    unittest.main()
