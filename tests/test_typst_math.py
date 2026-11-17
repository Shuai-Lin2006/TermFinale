import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tfv2.render.typst_math import convert_math, latex_to_typst_segments


class TypstMathTests(unittest.TestCase):
    def test_fraction_matrix_and_text(self) -> None:
        self.assertIn("(a+b)/(c)", convert_math(r"\frac{a+b}{c}"))
        self.assertIn('mat(delim: "("', convert_math(r"\begin{pmatrix}1&2\\3&4\end{pmatrix}"))
        self.assertIn('"秩"', convert_math(r"\text{秩}(A)=r(A)"))
        self.assertIn("CH₄", convert_math(r"\mathrm{CH_4}"))
        self.assertIn("∞", convert_math(r"\int_0^\infty e^{-t}dt"))

    def test_chemistry_and_physics(self) -> None:
        self.assertIn("H₂SO₄", convert_math(r"\ce{H2SO4}"))
        self.assertIn("→", convert_math(r"\ce{2H2 + O2 -> 2H2O}"))
        self.assertIn("arrow(F)", convert_math(r"\vec{F}=m\vec{a}"))
        self.assertIn("m/s²", convert_math(r"\SI{9.8}{m/s^2}"))
        self.assertIn("¹⁴₆C", convert_math(r"\ce{^{14}_{6}C}"))

    def test_physics_corpus_compiles_if_typst_available(self) -> None:
        typst = shutil.which("typst")
        if not typst:
            self.skipTest("typst CLI not installed")
        formulas = [
            r"\vec{F}=m\vec{a}",
            r"F=G\frac{m_1m_2}{r^2}",
            r"\nabla\cdot\vec{E}=\frac{\rho}{\varepsilon_0}",
            r"i\hbar\frac{\partial}{\partial t}\Psi=\hat{H}\Psi",
            r"\oint \vec{B}\cdot d\vec{l}=\mu_0 I",
            r"\begin{aligned}a&=b+c\\d&=e+f\end{aligned}",
        ]
        body = "\n".join("$ " + convert_math(f) + " $\n#v(0.2cm)" for f in formulas)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "p.typ"; src.write_text("#set page(width: 20cm, height: 20cm)\n" + body, encoding="utf-8")
            out = Path(td) / "p.pdf"
            r = subprocess.run([typst, "compile", str(src), str(out)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[:1000])

    def test_prose_math_segments(self) -> None:
        out = latex_to_typst_segments(r"功率 $P=UI$，能量 $W=\frac{1}{2}CU^2$。")
        self.assertIn("$P=U I$", out)
        self.assertIn("(1)/(2)", out)

    def test_real_subset_compiles_if_typst_available(self) -> None:
        typst = shutil.which("typst")
        if not typst:
            self.skipTest("typst CLI not installed")
        formulas = [
            r"u_C(t)=U\left(1-e^{-t/\tau}\right)",
            r"L=\frac{\psi}{i},\quad \psi=N\Phi",
            r"\begin{pmatrix}1&2\\3&4\end{pmatrix}",
            r"\text{秩}(A)=r(A)",
            r"\ce{2H2 + O2 -> 2H2O}",
            r"\vec{F}=m\vec{a}",
            r"\SI{9.8}{m/s^2}",
        ]
        body = "\n".join("$ " + convert_math(f) + " $\n#v(0.2cm)" for f in formulas)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "f.typ"
            src.write_text("#set page(width: 20cm, height: 20cm)\n" + body, encoding="utf-8")
            out = Path(td) / "f.pdf"
            r = subprocess.run([typst, "compile", str(src), str(out)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[:1000])
            self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
