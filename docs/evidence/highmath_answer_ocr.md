/Users/lan/PycharmProjects/TermFinale/.venv/lib/python3.14/site-packages/fitz/__init__.py:17: FutureWarning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
  warnings.warn(
===== PAGE 1 =====
1. $(\sqrt{} )$
2. $(\times) \quad f(x, y) \quad D \quad \iint_{D} f(x, y) dx dy$
3. $(\times)$
4. $(\times)$
5. $(\sqrt{} )$

1.

5 15

1. $a \perp b, a \bullet b = 0$.
2. $\lim _{(x, y) \rightarrow(0,0)} \frac{(x+y)}{\sin (x+y)} = 1$.
3. $P_{0} = (1, 3, 2), s = \left(1, \frac{1}{2}, 0\right)$
$\frac{x-1}{1} = \frac{y-3}{\frac{1}{2}} = \frac{z-2}{0}$

5 15

1. $f(x, y) = \begin{cases} \frac{x y}{x^{2} + y^{2}}, & x^{2} + y^{2} \neq 0 \\ 0, & x^{2} + y^{2} = 0 \end{cases}$ Error: Reference source not found (0, 0) (B).
A. B. C. D.

2. $a \parallel b = 0, a \quad b$ (B).
A. B. C.

3. $a \not\parallel b \quad |a - b| = |a| + |b| \quad a \not\parallel b$ (B).

10 50

1. $z = 2u^{3} - v^{2} + e^{w} + 1, \quad u = t + s - \ln r, v = \sqrt{s} - \sin r, w = \cos t - 7, \quad \frac{\partial z}{\partial t}, \frac{\partial z}{\partial s}, \frac{\partial z}{\partial r}$.

$\begin{aligned} \frac{\partial z}{\partial t} &= \frac{\partial z}{\partial u} \cdot \frac{\partial u}{\partial t} + \frac{\partial z}{\partial w} \cdot \frac{\partial w}{\partial t} \\ &= 6u^{2} \cdot 1 + e^{w} \cdot (-\sin t) \\ &= 6u^{2} - e^{w} \sin t, \end{aligned}$

$\begin{aligned} \frac{\partial z}{\partial s} &= \frac{\partial z}{\partial u} \cdot \frac{\partial u}{\partial s} + \frac{\partial z}{\partial v} \cdot \frac{\partial v}{\partial s} \\ &= 6u^{2} \cdot 1 + (-2v) \cdot \frac{1}{2\sqrt{s}} \\ &= 6u^{2} - \frac{v}{\sqrt{s}}, \end{aligned}$

$\begin{aligned} \frac{\partial z}{\partial r} &= \frac{\partial z}{\partial u} \cdot \frac{\partial u}{\partial r} + \frac{\partial z}{\partial v} \cdot \frac{\partial v}{\partial r} \\ &= 6u^{2} \cdot \left(-\frac{1}{r}\right) + (-2v) \cdot (\cos r) \\ &= 2v \cos r - \frac{6u^{2}}{r}. \end{aligned}$

2. $u = x^{3} + 3xy + y^{2} + x \ln z^{2}, \quad \frac{\partial u}{\partial x}, \frac{\partial u}{\partial z}$.
===== PAGE 2 =====
$\begin{aligned}& \frac{\partial u}{\partial x}=3 x^{2}+3 y+0+1 \cdot \ln z^{2} \\& =3 x^{2}+3 y+\ln z^{2} . \\& \frac{\partial u}{\partial z}=0+0+0+x \frac{1}{z^{2}}\left(z^{2}\right)^{\prime} \\& =\frac{2 x}{z}\end{aligned}$

3. $\int_{D} x \cos (x+y) d x d y \quad D \quad(0,0),(x, 0) \boxtimes(\pi, \pi)$

$\begin{aligned}& \iint_{D} x \cos (x+y) d \sigma=\int_{0}^{\pi} x d x \int_{0}^{x} \cos (x+y) d y \\& =\int_{0}^{\pi} x\left[\sin (x+y)\right]_{0}^{x} d x=\int_{0}^{\pi} x(\sin 2 x-\sin x) d x \\& =\int_{0}^{\pi} x d\left(\cos x-\frac{1}{2} \cos 2 x\right) \\& =\left[x\left(\cos x-\frac{1}{2} \cos 2 x\right)\right]_{0}^{\pi}-\int_{0}^{\pi}\left(\cos x-\frac{1}{2} \cos 2 x\right) d x \\& =\pi\left(-1-\frac{1}{2}\right)-0=-\frac{3}{2} \pi\end{aligned}$

4. $n=(2,-1,3), \quad P_{0}=(0,1,1)$

$2(x-0)+(-1)(y-1)+3(z-1)=0,$

$2 x-y+3 z=2$

5. $u^{2}-4 u=\ln z \cdot x y+1, \quad \frac{\partial u}{\partial x}, \frac{\partial x}{\partial y} \quad \frac{\partial y}{\partial u}$

$F(x, y, z, u)=u^{2}-4 u \cdot \ln z+x y-1=0,$

$F_{x}=\frac{\partial F}{\partial x}=y, \quad F_{y}=\frac{\partial F}{\partial y}=x,$

$F_{z}=\frac{\partial F}{\partial z}=\frac{1}{z}, \quad F_{u}=\frac{\partial F}{\partial u}=2 u-4,$

$\begin{aligned}\frac{\partial u}{\partial x} & =-\frac{F_{x}}{F_{u}}=-\frac{y}{2 u-4}=\frac{y}{4-2 u} \\\frac{\partial x}{\partial y} & =-\frac{F_{y}}{F_{x}}=-\frac{x}{y}, \\\frac{\partial y}{\partial u} & =-\frac{F_{u}}{F_{y}}=-\frac{2 u-4}{x}=\frac{4-2 u}{x}.\end{aligned}$

10

1. $f(x, y)=x^{3}-y^{2}+6 x y \quad(-6,-18)$

$\left\{\begin{array}{l}f_{x}=3 x^{2}+6 y=0 \\f_{y}=-2 y+6 x=0\end{array} \quad 0,0 \quad-6 \quad-18 .(2)\right.$

$0,0 \quad f_{x x}\left|_{(0,0)}=6 x\right|_{x=0}=0, f_{x y}\left|_{(0,0)}=6 \quad f_{y y}\left|_{(0,0)}=-2\right.$

$A C-B^{2}=-36<0, \quad 0,0 \quad .(3)$

$-6-18 \quad f_{x x}\left|_{(-6,-18)}=6 x\right|_{x=-36}, f_{x y}\left|_{(-6,-18)}=6 \quad f_{y y}\left|_{(-6,-18)}=-2\right.$
===== PAGE 3 =====
$\begin{array}{ll}\text { Ⅱ } & \text { 2025-2026 } 2 \quad 3 \\\text { AC - } B^{2}=36>0, & -6,-18 \quad .(3 \\\text { A<0 } & .(2\end{array}$
