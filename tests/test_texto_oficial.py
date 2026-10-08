# SPDX-License-Identifier: Apache-2.0
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import texto_oficial as T

PAGS = ["El Congreso de los Diputados insta al Gobierno a:\n1. Reforzar la red\nferroviaria.\n2. Otra cosa.",
        "ENMIENDA NÚM. 9\nGrupo X\nDe modificación.\nTexto <b>&</b> que se propone.\nENMIENDA NÚM. 10\nOtra"]

class TestLiteral(unittest.TestCase):
    def test_fragmento_con_saltos_distintos_es_literal(self):
        self.assertTrue(T.es_literal("1. Reforzar la red ferroviaria.", PAGS))
    def test_prefijo_nuestro_no_es_literal(self):
        self.assertFalse(T.es_literal("Texto resultante aprobado: 1. Reforzar la red ferroviaria.", PAGS))
    def test_descripcion_no_es_literal(self):
        self.assertFalse(T.es_literal("Pide reforzar el tren.", PAGS))
    def test_pagina(self):
        self.assertEqual(T.pagina_de("Texto <b>&</b> que se propone", PAGS), 2)
    def test_cortar_enmienda(self):
        t = T.cortar(PAGS, r"ENMIENDA NÚM\. 9\b", r"ENMIENDA NÚM\.")
        self.assertTrue(t.startswith("ENMIENDA NÚM. 9") and "que se propone." in t and "Otra" not in t)
    def test_cabecera_bocg_se_quita(self):
        p = T.limpiar("texto\ncve: BOCG-15-A-16-2\nBOLETÍN OFICIAL DE LAS CORTES GENERALES\nCONGRESO DE LOS DIPUTADOS\nSerie A Núm. 16-2 26 de junio de 2024 Pág. 2\nsigue\u200b")
        self.assertEqual(p, "texto\nsigue")

class TestFix(unittest.TestCase):
    def test_limpiar_conserva_lineas_de_cuerpo(self):
        txt = "CONGRESO DE LOS DIPUTADOS insta al Gobierno\nCORTES GENERALES, aprueba\nCONGRESO DE LOS DIPUTADOS\nCORTES GENERALES\n\nfin"
        self.assertEqual(T.limpiar(txt), "CONGRESO DE LOS DIPUTADOS insta al Gobierno\nCORTES GENERALES, aprueba\n\nfin")
    def test_pagina_de_empieza_en_pagina_1(self):
        pags = ["relleno inicial\nlas últimas palabras del texto que sigue", "y continúa en la segunda página con más texto"]
        self.assertEqual(T.pagina_de("las últimas palabras del texto que sigue y continúa en la segunda página", pags), 1)
    def test_parrafos(self):
        s = "El Congreso insta al\nGobierno a:\n1. Reforzar la red\nferroviaria.\n2. Otra\ncosa."
        r = T.parrafos(s)
        self.assertEqual(r, "El Congreso insta al Gobierno a:\n\n1. Reforzar la red ferroviaria.\n\n2. Otra cosa.")
        self.assertEqual(T.norm(r), T.norm(s))


class TestPdfReal(unittest.TestCase):
    PDF = Path("data/pdf_cache/BOCG-15-A-16-2.PDF")
    @unittest.skipUnless(PDF.exists(), "PDF de caché no disponible")
    def test_enmienda_1_real(self):
        pags = T.paginas_pdf(str(self.PDF))
        t = T.cortar(pags, r"ENMIENDA NÚM\. 1\b", r"ENMIENDA NÚM\.")
        self.assertIn("Enmienda a la totalidad de devolución", t)
        self.assertNotIn("cve: BOCG", t)
        self.assertTrue(T.es_literal(t, pags))

class TRecortar(unittest.TestCase):
    P = ["Previo.\nEl Congreso INSTA al Gobierno a: 1. Hacer cosas concretas;\n2. Otras cosas distintas. Fin."]
    def test_devuelve_puntuacion_del_pdf(self):
        r = T.recortar("el congreso insta al gobierno a 1 hacer cosas concretas", self.P)
        self.assertEqual(r, "El Congreso INSTA al Gobierno a: 1. Hacer cosas concretas;")
    def test_mitad_de_palabra_al_inicio(self):
        self.assertIsNone(T.recortar("ongreso INSTA al Gobierno a: 1. Hacer cosas", self.P))
    def test_mitad_de_palabra_al_final(self):
        self.assertIsNone(T.recortar("El Congreso INSTA al Gobierno a: 1. Hacer cosas conc", self.P))


if __name__ == "__main__":
    unittest.main()
