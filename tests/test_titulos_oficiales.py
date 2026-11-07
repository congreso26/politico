# SPDX-License-Identifier: Apache-2.0
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import titulos_oficiales as TO

class T(unittest.TestCase):
    def test_fila(self):
        d = {"informacion": {"textoExpediente": "Proyecto de Ley X.\n", "tituloSubGrupo": "Enmiendas",
                             "textoSubGrupo": "Enmiendas 740, 768 y 776."}}
        self.assertEqual(TO.fila_titulo(d, 76, 3), {"sesion": 76, "num_votacion": 3,
            "texto_expediente": "Proyecto de Ley X.", "titulo_subgrupo": "Enmiendas",
            "texto_subgrupo": "Enmiendas 740, 768 y 776."})

if __name__ == "__main__":
    unittest.main()
