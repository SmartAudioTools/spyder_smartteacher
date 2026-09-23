"""Le fichier de l'eleve s'appelle NOM_Prenom_TP_xxxx.py (demande de l'utilisateur, 23/09/2026)."""

import unittest

from spyder_smartteacher.tp import eleve_depuis_env, nom_fichier


class NomFichier(unittest.TestCase):
    def test_forme(self):
        self.assertEqual(nom_fichier("Dupont", "marie", "monkey"), "DUPONT_Marie_TP_monkey.py")

    def test_accents_gardes_espaces_en_tiret(self):
        self.assertEqual(nom_fichier("de la Fontaine", "jean-éric", "tp 1"), "DE-LA-FONTAINE_Jean-Éric_TP_tp-1.py")

    def test_caracteres_interdits(self):
        self.assertEqual(nom_fichier("o'brien/x", "ana:bel", "a*b"), "O-BRIEN-X_Ana-Bel_TP_a-b.py")

    def test_prenom_compose_garde_ses_majuscules(self):
        self.assertEqual(nom_fichier("MARTIN", "Jean Pierre", "t"), "MARTIN_Jean-Pierre_TP_t.py")

    def test_env(self):
        # Les variables posees par le poste de l'eleve (ELEVE_ID, le nom du coffre, ne sert pas au nom du fichier).
        env = {"ELEVE_ID": "lefevre_zoe", "ELEVE_NOM": " Lefèvre ", "ELEVE_PRENOM": "Zoé"}
        self.assertEqual(eleve_depuis_env(env), ("Lefèvre", "Zoé"))
        self.assertEqual(nom_fichier(*eleve_depuis_env(env), "pyxel_projet_monkey"),
                         "LEFÈVRE_Zoé_TP_pyxel-projet-monkey.py")

    def test_env_absente_ou_vide(self):
        self.assertIsNone(eleve_depuis_env({}))
        self.assertIsNone(eleve_depuis_env({"ELEVE_NOM": "Dupont", "ELEVE_PRENOM": "  "}))


if __name__ == "__main__":
    unittest.main()
