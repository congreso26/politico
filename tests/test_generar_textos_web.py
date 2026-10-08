# SPDX-License-Identifier: Apache-2.0
import sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generar_textos_web as G


class T(unittest.TestCase):
    def test_quita_prefijo_y_corchetes_de_texto_votado(self):
        f = {"sesion": "13", "num_votacion": "4", "fuente_texto": "https://x/BOCG-15-D-1.PDF",
             "texto_votado": "Texto resultante aprobado: El Congreso insta a: 1. Algo largo de verdad."}
        locs = G.localizadores_auto(f)
        self.assertEqual(locs[0]["sel"], {"literal": "El Congreso insta a: 1. Algo largo de verdad."})

    def test_truncado_no_genera_localizador_literal(self):
        f = {"sesion": "1", "num_votacion": "1", "fuente_texto": "u", "texto_votado": "Inicio del texto […]"}
        self.assertEqual(G.localizadores_auto(f), [])

    def test_truncado_con_puntos_suspensivos(self):
        f = {"sesion": "1", "num_votacion": "1", "fuente_texto": "u", "texto_votado": "Texto cortado a media pala…"}
        self.assertEqual(G.localizadores_auto(f), [])

    def test_empieza_en_el_congreso(self):
        f = {"sesion": "1", "num_votacion": "1", "fuente_texto": "u",
             "texto_votado": "presenta la siguiente Moción «El Congreso de los Diputados insta a: 1. Algo."}
        self.assertEqual(G.localizadores_auto(f)[0]["sel"], {"literal": "El Congreso de los Diputados insta a: 1. Algo."})

    def test_corta_boilerplate_final(self):
        for fin in ("Se ordena la publicación de conformidad", "Palacio del Congreso de los Diputados, 1", "Lo que se publica"):
            f = {"sesion": "1", "num_votacion": "1", "fuente_texto": "u",
                 "texto_votado": f"El Congreso de los Diputados insta a: 1. Algo. {fin} con lo dispuesto."}
            self.assertEqual(G.localizadores_auto(f)[0]["sel"], {"literal": "El Congreso de los Diputados insta a: 1. Algo."})

    def test_extrae_texto_crudo_del_pdf(self):
        pags = ["El Congreso INSTA al Gobierno a: 1. Hacer cosas concretas."]
        with mock.patch.object(G.texto_oficial, "paginas_pdf", return_value=pags):
            G.paginas.cache_clear()
            r = G.extraer({"id": "x", "doc": "u", "sel": {"literal": "el congreso insta al gobierno a 1 hacer cosas concretas"}})
        G.paginas.cache_clear()
        self.assertEqual(r["texto"], "El Congreso INSTA al Gobierno a: 1. Hacer cosas concretas.")

    def test_registro_esquema(self):
        r = G.registro("76-3", {"texto_expediente": "Proyecto X.", "titulo_subgrupo": "Enmiendas",
                       "texto_subgrupo": "Enmienda 9."}, [], False, "121/000016")
        self.assertEqual(r["estado"], "sin_texto")
        self.assertEqual(r["subgrupo"], "Enmiendas · Enmienda 9.")
        self.assertIn("_iniciativas_id=121/000016", r["fuente_ficha"])
        self.assertEqual(set(r), {"id", "titulo", "subgrupo", "estado", "fragmentos", "fuente_ficha"})

    def test_extraer_rechaza_no_literal(self):
        pags = ["El Congreso insta al Gobierno a: 1. Hacer cosas concretas."]
        with mock.patch.object(G.texto_oficial, "paginas_pdf", return_value=pags):
            G.paginas.cache_clear()
            self.assertIsNone(G.extraer({"id": "x", "doc": "u", "sel": {"literal": "Pide hacer cosas concretas al Gobierno."}}))
            self.assertEqual(G.extraer({"id": "x", "doc": "u", "sel": {"literal": "1. Hacer cosas concretas"}})["pagina"], 1)
        G.paginas.cache_clear()


if __name__ == "__main__":
    unittest.main()
