"""La seance : ouvrir un paquet, creer ou retrouver le fichier de l'eleve et son journal, photographier l'onglet actif.

Sans Spyder ni pont : un pont factice (memes methodes que client.Pont) et un editeur factice (les trois gestes que
le greffon demande a l'editeur de Spyder).
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from spyder_smartteacher.client import PontErreur
from spyder_smartteacher.seance import Seance
from spyder_smartteacher.tp import SOUMISE, TRAITEE
from tests.test_session import Correcteur, etapes

ENV = {"ELEVE_NOM": "Lefèvre", "ELEVE_PRENOM": "Zoé"}
NOM = "LEFÈVRE_Zoé_TP_pyxel-projet-monkey.py"


class PontFactice:
    """Paquet protege par « secret » ; le journal est garde en clair dans un dict (le chiffrement est teste ailleurs)."""

    def __init__(self, mot_de_passe="secret"):
        self.mot_de_passe, self.journaux, self.corriger = mot_de_passe, {}, Correcteur()

    def ouvrir(self, paquet, mot_de_passe=None):
        if self.mot_de_passe and mot_de_passe != self.mot_de_passe:
            raise PontErreur("mot de passe incorrect" if mot_de_passe else "mot de passe requis", True)
        return {"titre": "Créer un jeu", "etapes": etapes()}

    def sauver_journal(self, chemin, journal):
        self.journaux[str(chemin)] = journal
        Path(chemin).write_text("chiffré")

    def charger_journal(self, chemin):
        return self.journaux[str(chemin)]


class EditeurFactice:
    def __init__(self):
        self.ouverts, self.actif, self.enregistrements = [], None, 0
        self.tampon = {}  # texte tape mais pas encore enregistre, par fichier

    def ouvrir(self, chemin):
        self.ouverts.append(chemin)
        self.actif = chemin

    def fichier_actif(self):
        return self.actif

    def enregistrer_actif(self):
        self.enregistrements += 1
        if self.actif in self.tampon:
            Path(self.actif).write_text(self.tampon.pop(self.actif))


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dossier)
        self.paquet = self.dossier / "pyxel_projet_monkey.qcm"
        self.pont, self.editeur = PontFactice(), EditeurFactice()
        self.mots_de_passe = None  # None : toujours le bon ; une liste : les reponses successives de l'eleve
        self.questions, self.confirmations = [], []
        self.eleve = None
        self.seance = self.nouvelle()

    def nouvelle(self):
        return Seance(self.pont, self.editeur, demander_mot_de_passe=self.demander_mot_de_passe,
                      demander_eleve=lambda: self.eleve, environ=ENV)

    def demander_mot_de_passe(self, erreur):
        self.questions.append(erreur)
        if self.mots_de_passe is None:
            return "secret"
        return self.mots_de_passe.pop(0) if self.mots_de_passe else None

    def confirmer_oui(self, question):
        self.confirmations.append(question)
        return True


class Ouvrir(Base):
    def test_cree_le_fichier_avec_le_code_initial_et_l_ouvre(self):
        session, titre = self.seance.ouvrir(self.paquet)
        fichier = self.dossier / NOM
        self.assertEqual(titre, "Créer un jeu")
        self.assertEqual(fichier.read_text(), "# depart\n")
        self.assertEqual(self.editeur.ouverts, [str(fichier)])
        self.assertEqual(session.fichier, str(fichier))
        self.assertTrue((self.dossier / "LEFÈVRE_Zoé_TP_pyxel-projet-monkey.journal").is_file())

    def test_ne_recrase_pas_un_fichier_existant(self):
        (self.dossier / NOM).write_text("mon travail")
        self.seance.ouvrir(self.paquet)
        self.assertEqual((self.dossier / NOM).read_text(), "mon travail")

    def test_mot_de_passe_redemande_puis_abandon(self):
        self.mots_de_passe = ["faux", "secret"]
        self.assertIsNotNone(self.seance.ouvrir(self.paquet))
        self.assertEqual(self.questions, ["mot de passe requis", "mot de passe incorrect"])
        self.mots_de_passe = []
        self.assertIsNone(self.nouvelle().ouvrir(self.paquet))

    def test_paquet_sans_mot_de_passe(self):
        self.pont.mot_de_passe = None
        self.mots_de_passe = []
        self.assertIsNotNone(self.seance.ouvrir(self.paquet))
        self.assertEqual(self.questions, [])

    def test_autre_erreur_du_pont_remonte(self):
        def panne(paquet, mot_de_passe=None):
            raise PontErreur("paquet illisible")
        self.pont.ouvrir = panne
        with self.assertRaises(PontErreur):
            self.seance.ouvrir(self.paquet)

    def test_nom_demande_si_l_environnement_ne_le_donne_pas(self):
        self.eleve = ("dupont", "marie")
        seance = Seance(self.pont, self.editeur, self.demander_mot_de_passe, lambda: self.eleve, environ={})
        session, _ = seance.ouvrir(self.paquet)
        self.assertEqual(Path(session.fichier).name, "DUPONT_Marie_TP_pyxel-projet-monkey.py")
        self.eleve = None
        self.assertIsNone(Seance(self.pont, self.editeur, self.demander_mot_de_passe, lambda: None,
                                 environ={}).ouvrir(self.paquet))


class Reprise(Base):
    def test_le_journal_est_recharge(self):
        session, _ = self.seance.ouvrir(self.paquet)
        session.soumettre(0, "juste")
        self.seance.sauver()
        self.editeur.ouverts.clear()
        reprise, _ = self.nouvelle().ouvrir(self.paquet)
        self.assertEqual(reprise.statut(0), SOUMISE)
        self.assertEqual(self.editeur.ouverts, [str(self.dossier / NOM)])

    def test_le_fichier_lie_est_rouvert(self):
        autre = self.dossier / "monkey.py"
        autre.write_text("x")
        self.seance.ouvrir(self.paquet)
        self.seance.lier(str(autre))
        self.editeur.ouverts.clear()
        reprise, _ = self.nouvelle().ouvrir(self.paquet)
        self.assertEqual(reprise.fichier, str(autre))
        self.assertEqual(self.editeur.ouverts, [str(autre)])

    def test_fichier_lie_disparu_recree_le_fichier_par_defaut(self):
        autre = self.dossier / "monkey.py"
        autre.write_text("x")
        self.seance.ouvrir(self.paquet)
        self.seance.lier(str(autre))
        autre.unlink()
        reprise, _ = self.nouvelle().ouvrir(self.paquet)
        self.assertEqual(reprise.fichier, str(self.dossier / NOM))


class Photo(Base):
    def setUp(self):
        super().setUp()
        self.session, _ = self.seance.ouvrir(self.paquet)
        self.fichier = self.session.fichier

    def test_enregistre_puis_lit_le_disque(self):
        self.editeur.tampon[self.fichier] = "tapé pas enregistré"
        self.assertEqual(self.seance.photo(self.confirmer_oui), "tapé pas enregistré")
        self.assertEqual(self.confirmations, [])  # c'est le bon fichier : rien a confirmer

    def test_autre_onglet_actif_confirme_avec_les_deux_noms(self):
        essai = self.dossier / "essai.py"
        essai.write_text("essai")
        self.editeur.ouvrir(str(essai))
        self.assertEqual(self.seance.photo(self.confirmer_oui), "essai")
        self.assertIn("essai.py", self.confirmations[0])
        self.assertIn(NOM, self.confirmations[0])
        self.assertIsNone(self.seance.photo(lambda question: False))

    def test_aucun_onglet_lit_le_fichier_lie(self):
        self.editeur.actif = None
        Path(self.fichier).write_text("sur le disque")
        self.assertEqual(self.seance.photo(self.confirmer_oui), "sur le disque")
        self.assertEqual(self.editeur.enregistrements, 0)


class Renommer(Base):
    def test_enregistrer_sous_suit_le_fichier_lie(self):
        session, _ = self.seance.ouvrir(self.paquet)
        nouveau = str(self.dossier / "monkey_final.py")
        Path(nouveau).write_text("x")  # ecrit par Spyder avant d'emettre le renommage
        self.seance.renomme(session.fichier, nouveau)
        self.assertEqual(session.fichier, nouveau)
        self.assertEqual(self.nouvelle().ouvrir(self.paquet)[0].fichier, nouveau)  # journal enregistre

    def test_un_autre_fichier_renomme_ne_change_rien(self):
        session, _ = self.seance.ouvrir(self.paquet)
        avant = session.fichier
        self.seance.renomme(str(self.dossier / "essai.py"), str(self.dossier / "essai2.py"))
        self.assertEqual(session.fichier, avant)

    def test_sans_session_rien_ne_casse(self):
        self.seance.renomme("a.py", "b.py")


class Lier(Base):
    def test_lier_ouvre_et_enregistre(self):
        session, _ = self.seance.ouvrir(self.paquet)
        autre = self.dossier / "monkey.py"
        autre.write_text("x")
        self.seance.lier(str(autre))
        self.assertEqual(self.editeur.actif, str(autre))
        session.marquer(0, "x")
        self.seance.sauver()
        self.assertEqual(self.nouvelle().ouvrir(self.paquet)[0].statut(0), TRAITEE)


if __name__ == "__main__":
    unittest.main()
