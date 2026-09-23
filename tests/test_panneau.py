"""Le panneau du dock : l'affichage d'une Session, sans Spyder ni pont (correcteur factice, offscreen).

Disposition du lecteur .qcm en mode « question » : une entete (titre, barre d'avancement, navigation, Terminer,
total), puis une etape par ecran (numero et bareme, enonce, aide et indices vus, boutons, retour de la correction).

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

    def entete(self):
        """Ce qu'affiche la tete de l'etape courante : numero, statut, bareme ou note."""
        return self.p.rang.text() + " " + self.p.gris.text()


class Affichage(Base):
    def test_premiere_etape_ouverte(self):
        self.assertEqual(self.p.i, 0)
        self.assertIn("Étape n°1", self.p.rang.text())
        self.assertIn("Etape 1", self.p.enonce.text())
        self.assertIsNotNone(self.session.journal["etapes"]["e1"]["ouverte"])
        self.assertIsNone(self.session.journal["etapes"]["e2"]["ouverte"])
        self.assertIn(A_FAIRE, self.entete())
        self.assertIn("2 points", self.entete())
        self.assertIn("0 / 4", self.p.total.text())
        self.assertEqual(self.p.barre_avancement.value(), 0)

    def test_precedent_suivant(self):
        self.assertFalse(self.p.precedent.isEnabled())
        self.p.suivant.click()
        self.assertIn("Etape 2", self.p.enonce.text())
        self.assertIsNotNone(self.session.journal["etapes"]["e2"]["ouverte"])
        self.assertFalse(self.p.bouton_aide.isEnabled())  # pas d'aide pour l'etape 2
        self.p.suivant.click()
        self.assertFalse(self.p.suivant.isEnabled())
        self.p.precedent.click()
        self.assertEqual(self.p.i, 1)

    def test_non_traitee_saute_les_etapes_rendues(self):
        self.p.aller(1)
        self.p.bouton_marquer.click()
        self.p.aller(0)
        self.p.suiv_libre.click()
        self.assertEqual(self.p.i, 2)  # l'etape 2 est traitee : sautee
        self.assertFalse(self.p.suiv_libre.isEnabled())
        self.p.prec_libre.click()
        self.assertEqual(self.p.i, 0)
        self.assertFalse(self.p.prec_libre.isEnabled())

    def test_barre_d_avancement(self):
        self.p.bouton_soumettre.click()
        self.assertEqual(self.p.barre_avancement.value(), 33)
        self.p.aller(1)
        self.p.bouton_marquer.click()
        self.assertEqual(self.p.barre_avancement.value(), 67)


class AideEtIndices(Base):
    def test_aide(self):
        self.p.bouton_aide.click()
        self.assertIn("partie « blt »", self.p.zone_aide.text())  # sous l'enonce, au-dessus des boutons
        self.assertTrue(self.session.journal["etapes"]["e1"]["aidee"])
        self.assertEqual(self.sauvegardes, [1])

    def test_indice_attend_son_delai(self):
        self.assertFalse(self.p.bouton_indice.isEnabled())
        self.assertIn("60 s", self.p.bouton_indice.text())
        self.horloge.t += 60
        self.p.rafraichir()
        self.assertTrue(self.p.bouton_indice.isEnabled())
        self.p.bouton_indice.click()
        self.assertIn("regarde la ligne 3", self.p.zone_aide.text())
        self.assertIn("60 s", self.p.bouton_indice.text())  # le second attend encore

    def test_indices_vus_restent_affiches(self):
        self.horloge.t += 60
        self.p.rafraichir()
        self.p.bouton_indice.click()
        self.p.aller(1)
        self.p.aller(0)
        self.assertIn("regarde la ligne 3", self.p.zone_aide.text())


class Soumettre(Base):
    def test_soumission_notee_et_gelee(self):
        self.p.bouton_soumettre.click()
        self.assertEqual(self.session.statut(0), SOUMISE)
        self.assertEqual(self.correcteur.appels, [("e1", "juste")])
        self.assertIn("2 / 2", self.entete())
        self.assertIn("corrige e1", self.p.retour.text())
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
        self.assertIn("le pont s'est arrêté", self.p.retour.text())


class Marquer(Base):
    def test_marquer_sans_note(self):
        self.p.bouton_marquer.click()
        self.assertEqual(self.session.statut(0), TRAITEE)
        self.assertIn(TRAITEE, self.entete())
        self.assertEqual(self.correcteur.appels, [])
        self.assertTrue(self.p.bouton_soumettre.isEnabled())
        self.assertEqual(self.sauvegardes, [1])


class Terminer(Base):
    def test_terminer(self):
        self.p.bouton_soumettre.click()
        self.p.aller(1)
        self.texte = "moitie"
        self.p.bouton_marquer.click()
        self.texte = "final"
        self.p.bouton_terminer.click()
        self.assertTrue(self.session.fini)
        self.assertEqual([self.session.statut(i) for i in range(3)], [SOUMISE, CORRIGEE, CORRIGEE])
        self.assertIn("2.5 / 4", self.p.total.text())
        for bouton in (self.p.bouton_soumettre, self.p.bouton_marquer, self.p.bouton_terminer, self.p.bouton_indice):
            self.assertFalse(bouton.isEnabled())
        self.p.aller(2)
        self.assertIn("fichier final", self.p.retour.text())  # le repli se dit

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
        self.assertIn(CORRIGEE, p.gris.text())


try:
    from spyder.utils.stylesheet import APP_STYLESHEET
except ImportError:
    APP_STYLESHEET = None


@unittest.skipIf(APP_STYLESHEET is None, "Spyder absent de ce Python")
class CouleursDuLecteur(Base):
    """Sous le theme sombre de Spyder (sa vraie feuille de style), le panneau garde les couleurs claires du lecteur :
    texte fonce sur fond clair, boutons compris. Constate avant : consignes en blanc sur noir, difficiles a lire."""

    def setUp(self):
        app.setStyleSheet(str(APP_STYLESHEET))
        self.addCleanup(app.setStyleSheet, "")
        super().setUp()
        self.p.resize(600, 500)
        self.p.show()
        app.processEvents()
        self.image = self.p.grab().toImage()

    def zone(self, widget):
        """Lumiere du fond (la mediane : le texte n'occupe qu'une petite part) et du trait le plus sombre."""
        r = widget.rect().translated(widget.mapTo(self.p, widget.rect().topLeft()))
        valeurs = [self.image.pixelColor(x, y).lightness() for x in range(r.left(), r.right(), 2)
                   for y in range(r.top(), r.bottom(), 2)]
        return sorted(valeurs)[len(valeurs) // 2], min(valeurs)

    def test_texte_fonce_sur_fond_clair(self):
        for widget in (self.p.enonce, self.p.rang, self.p.suivant, self.p.bouton_terminer):
            fond, sombre = self.zone(widget)
            self.assertGreater(fond, 200, widget)
            self.assertLess(sombre, 90, widget)


if __name__ == "__main__":
    unittest.main()
