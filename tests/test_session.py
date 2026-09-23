"""La session d'un TP : aide, indices, soumission (photo notee et gelee), marquage (photo notee a la fin), fin."""

import unittest

from spyder_smartteacher.tp import A_FAIRE, CORRIGEE, SOUMISE, TRAITEE, Session, TPFini


def etapes():
    return [{"id": "e1", "enonce": "Etape 1", "points": 2, "aide": "cours, partie « blt »", "code_initial": "# depart\n",
             "indices": [{"texte": "regarde la ligne 3", "delai": 60, "malus": 0.25},
                         {"texte": "il faut un elif", "delai": 120, "malus": 0.25}]},
            {"id": "e2", "enonce": "Etape 2", "points": 1, "aide": "", "indices": []},
            {"id": "e3", "enonce": "Etape 3", "points": 1, "aide": "", "indices": []}]


class Horloge:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Correcteur:
    """Juste si le texte contient « juste », a moitie s'il contient « moitie » ; garde la trace des appels."""

    def __init__(self):
        self.appels = []

    def __call__(self, id, texte):
        self.appels.append((id, texte))
        return (1.0 if "juste" in texte else 0.5 if "moitie" in texte else 0.0), [f"corrige {id}"]


class Base(unittest.TestCase):
    def setUp(self):
        self.horloge, self.correcteur = Horloge(), Correcteur()
        self.s = Session(etapes(), correcteur=self.correcteur, horloge=self.horloge)


class Aide(Base):
    def test_aide_gratuite_et_notee_comme_vue(self):
        self.assertEqual(self.s.voir_aide(0), "cours, partie « blt »")
        self.assertTrue(self.s.journal["etapes"]["e1"]["aidee"])
        self.s.soumettre(0, "juste")
        self.assertEqual(self.s.note(0), 2)


class Indices(Base):
    def test_delai_compte_depuis_la_premiere_ouverture(self):
        self.s.ouvrir(0)
        self.assertEqual(self.s.attente_indice(0), 60)
        self.horloge.t += 45
        self.s.ouvrir(0)  # rouvrir ne remet pas le compteur a zero
        self.assertEqual(self.s.attente_indice(0), 15)
        self.assertIsNone(self.s.debloquer_indice(0))
        self.horloge.t += 15
        self.assertEqual(self.s.debloquer_indice(0), "regarde la ligne 3")
        self.assertEqual(self.s.attente_indice(0), 60)  # le second : 120 s apres l'ouverture
        self.horloge.t += 60
        self.assertEqual(self.s.debloquer_indice(0), "il faut un elif")
        self.assertIsNone(self.s.attente_indice(0))  # plus d'indice
        self.assertEqual(self.s.indices_vus(0), ["regarde la ligne 3", "il faut un elif"])

    def test_malus_des_indices_debloques(self):
        self.s.ouvrir(0)
        self.horloge.t += 60
        self.s.debloquer_indice(0)
        self.s.soumettre(0, "juste")
        self.assertEqual(self.s.note(0), 1.5)  # 2 x (1 - 0.25)

    def test_note_jamais_negative(self):
        self.s.ouvrir(0)
        self.horloge.t += 200
        self.s.debloquer_indice(0)
        self.s.debloquer_indice(0)
        self.s.soumettre(0, "moitie")
        self.assertEqual(self.s.note(0), 0)

    def test_pas_d_indice_sans_indices(self):
        self.s.ouvrir(1)
        self.assertIsNone(self.s.attente_indice(1))
        self.assertIsNone(self.s.debloquer_indice(1))


class Soumettre(Base):
    def test_photo_corrigee_tout_de_suite_puis_gelee(self):
        self.assertEqual(self.s.statut(0), A_FAIRE)
        self.s.soumettre(0, "juste v1")
        self.assertEqual(self.s.statut(0), SOUMISE)
        self.assertEqual(self.s.note(0), 2)
        self.assertEqual(self.s.messages(0), ["corrige e1"])
        self.assertEqual(self.s.journal["etapes"]["e1"]["photo"], "juste v1")
        with self.assertRaises(TPFini):
            self.s.soumettre(0, "faux")
        self.assertEqual(self.s.note(0), 2)
        self.assertFalse(self.s.modifiable(0))

    def test_etape_suivante_non_touchee(self):
        self.s.soumettre(0, "juste")
        self.assertEqual(self.s.statut(1), A_FAIRE)
        self.assertIsNone(self.s.note(1))

    def test_sans_tests_la_note_attend_le_professeur(self):
        s = Session(etapes(), correcteur=lambda id, texte: (None, None), horloge=self.horloge)
        s.soumettre(0, "x")
        self.assertEqual(s.statut(0), SOUMISE)
        self.assertIsNone(s.note(0))


class Marquer(Base):
    def test_photo_gardee_sans_correction(self):
        self.s.marquer(1, "juste etape 2")
        self.assertEqual(self.s.statut(1), TRAITEE)
        self.assertIsNone(self.s.note(1))
        self.assertEqual(self.correcteur.appels, [])
        self.assertTrue(self.s.modifiable(1))

    def test_remarquer_remplace_la_photo(self):
        self.s.marquer(1, "v1")
        self.s.marquer(1, "juste v2")
        self.assertEqual(self.s.journal["etapes"]["e2"]["photo"], "juste v2")

    def test_une_traitee_peut_encore_etre_soumise(self):
        self.s.marquer(1, "v1")
        self.s.soumettre(1, "juste")
        self.assertEqual(self.s.note(1), 1)


class Terminer(Base):
    def test_corrige_les_photos_traitees_et_le_fichier_final_pour_le_reste(self):
        self.s.soumettre(0, "juste")
        self.s.marquer(1, "moitie photo")
        self.s.terminer("final")
        self.assertEqual(self.correcteur.appels, [("e1", "juste"), ("e2", "moitie photo"), ("e3", "final")])
        self.assertEqual([self.s.statut(i) for i in range(3)], [SOUMISE, CORRIGEE, CORRIGEE])
        self.assertEqual([self.s.note(i) for i in range(3)], [2, 0.5, 0])
        self.assertFalse(self.s.repli(1))
        self.assertTrue(self.s.repli(2))  # corrigee sur le fichier final : le dock le dit
        self.assertEqual(self.s.total(), (2.5, 4))
        self.assertEqual(self.s.journal["final"], "final")

    def test_plus_rien_ne_bouge_apres_la_fin(self):
        self.s.terminer("final")
        self.assertTrue(self.s.fini)
        for action in (lambda: self.s.soumettre(0, "juste"), lambda: self.s.marquer(0, "juste"),
                       lambda: self.s.terminer("juste")):
            with self.assertRaises(TPFini):
                action()
        self.assertFalse(self.s.modifiable(0))


class Journal(Base):
    def test_reprise_depuis_le_journal(self):
        self.s.ouvrir(0)
        self.horloge.t += 60
        self.s.debloquer_indice(0)
        self.s.soumettre(0, "juste")
        self.s.marquer(1, "photo 2")
        self.s.fichier = "/chemin/DUPONT_Marie_TP_x.py"
        reprise = Session(etapes(), journal=self.s.journal, correcteur=self.correcteur, horloge=self.horloge)
        self.assertEqual(reprise.note(0), 1.5)
        self.assertEqual(reprise.statut(1), TRAITEE)
        self.assertEqual(reprise.indices_vus(0), ["regarde la ligne 3"])
        self.assertEqual(reprise.fichier, "/chemin/DUPONT_Marie_TP_x.py")
        self.assertFalse(reprise.modifiable(0))

    def test_journal_en_donnees_simples(self):
        import json
        self.s.soumettre(0, "juste")
        self.assertEqual(json.loads(json.dumps(self.s.journal)), self.s.journal)


if __name__ == "__main__":
    unittest.main()
