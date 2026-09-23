"""Le fichier de l'eleve s'appelle NOM_Prenom_TP_xxxx.py (demande de l'utilisateur, 23/09/2026)."""

import unittest

from spyder_smartteacher.tp import VAR_NOM, VAR_PRENOM, eleve_depuis_env, nom_fichier


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
        self.assertEqual(eleve_depuis_env({VAR_NOM: " Dupont ", VAR_PRENOM: "Marie"}), ("Dupont", "Marie"))

    def test_env_absente_ou_vide(self):
        self.assertIsNone(eleve_depuis_env({}))
        self.assertIsNone(eleve_depuis_env({VAR_NOM: "Dupont", VAR_PRENOM: "  "}))


if __name__ == "__main__":
    unittest.main()
