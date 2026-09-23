"""Le pont : le vrai paquet Monkey ouvert dans le Python du QCM, corrige par Code.corriger, journal chiffre.

Le greffon tourne dans le venv de Spyder (PyQt5) et n'importe jamais modele.py (PySide6) : tout passe par ce
processus a part. Le test est donc lent (le chiffrement scrypt coute ~4 s a l'ouverture) et exige le paquet
exporte : Exports/eleve/pyxel_projet_monkey.qcm (exporter_eleve.py sujets/pyxel_projet_monkey.json).
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from spyder_smartteacher.client import NON_TRANSMISES, Pont, PontErreur, python_qcm, dossier_qcm
from spyder_smartteacher.tp import SOUMISE, Session

PAQUET = Path(os.environ.get("SMARTTEACHER_TEST_PAQUET", Path(dossier_qcm()) / "Exports/eleve/pyxel_projet_monkey.qcm"))


def solutions():
    """Les solutions, lues a part : le pont, lui, ne les donne jamais au greffon."""
    code = ("import json, sys\nfrom voir import ouvrir\np, _ = ouvrir(sys.argv[1], None, False)\n"
            "print('@@' + json.dumps({f.id: f.solution for q in p.questions() for f in q.feuilles()}))")
    sortie = subprocess.run([python_qcm(), "-c", code, str(PAQUET)], cwd=dossier_qcm(), capture_output=True, text=True,
                            env={**{k: v for k, v in os.environ.items() if k not in NON_TRANSMISES},
                                 "QT_QPA_PLATFORM": "offscreen"}, check=True).stdout
    return json.loads(next(ligne for ligne in sortie.splitlines() if ligne.startswith("@@"))[2:])


@unittest.skipUnless(PAQUET.is_file(), f"paquet absent : {PAQUET}")
class PontMonkey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Le pont ne doit pas dependre de la liaison de Spyder : QT_API=pyqt6 (le lanceur du Raspberry Pi, sans
        # PySide6) ferait passer qtpy6, donc modele.py, sous PyQt6 ; une valeur qu'il ignore l'empecherait de demarrer.
        avant = os.environ.get("QT_API")
        os.environ["QT_API"] = "pyqt5"
        try:
            cls.pont = Pont()
        finally:
            os.environ.pop("QT_API") if avant is None else os.environ.__setitem__("QT_API", avant)
        cls.sujet = cls.pont.ouvrir(PAQUET)
        cls.etapes = cls.sujet["etapes"]
        cls.solutions = solutions()

    @classmethod
    def tearDownClass(cls):
        cls.pont.fermer()

    def test_etapes(self):
        self.assertEqual(self.sujet["titre"], "Créer un jeu")
        self.assertEqual(len(self.etapes), 31)
        e = self.etapes[0]
        self.assertEqual(e["id"], "nsi->premiere->pyxel->monkey_01")
        self.assertEqual(e["titre"], "Créer un jeu de plateforme minimal")
        self.assertEqual(set(e), {"id", "titre", "enonce", "points", "aide", "indices", "code_initial"})

    def test_rien_de_la_correction_ne_sort(self):
        texte = json.dumps(self.sujet)
        for solution in list(self.solutions.values())[:5]:
            self.assertNotIn(json.dumps(solution)[1:-1], texte)

    def test_correction_de_la_photo(self):
        id3, id2 = self.etapes[2]["id"], self.etapes[1]["id"]
        self.assertEqual(self.pont.corriger(id3, self.solutions[id3]), (1.0, []))
        fraction, messages = self.pont.corriger(id3, self.solutions[id2])  # l'etape 2 ne recule pas encore
        self.assertEqual(fraction, 0.0)
        self.assertTrue(any("gauche" in m for m in messages), messages)

    def test_session_branchee_sur_le_pont(self):
        s = Session(self.etapes, correcteur=self.pont.corriger)
        s.soumettre(2, self.solutions[self.etapes[2]["id"]])
        self.assertEqual((s.statut(2), s.note(2)), (SOUMISE, self.etapes[2]["points"]))

    def test_journal_chiffre(self):
        journal = {"fichier": "/x/DUPONT_Marie_TP_monkey.py", "fin": None, "final": None,
                   "etapes": {"e1": {"photo": "secret_photo = 1"}}}
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "j.journal"
            self.pont.sauver_journal(chemin, journal)
            self.assertNotIn(b"secret_photo", chemin.read_bytes())
            self.assertEqual(self.pont.charger_journal(chemin), journal)

    def test_erreur_rapportee_sans_tuer_le_pont(self):
        with self.assertRaises(PontErreur):
            self.pont.corriger("inconnue", "x")
        self.assertEqual(len(self.pont.ouvrir(PAQUET)["etapes"]), 31)  # toujours vivant


class PontMotDePasse(unittest.TestCase):
    @unittest.skipUnless(PAQUET.is_file(), f"paquet absent : {PAQUET}")
    def test_mauvais_mot_de_passe(self):
        pont = Pont()
        try:
            with self.assertRaises(PontErreur) as e:
                pont.ouvrir(PAQUET, "pas le bon")
            self.assertIn("mot de passe", str(e.exception))
        finally:
            pont.fermer()


if __name__ == "__main__":
    unittest.main()
