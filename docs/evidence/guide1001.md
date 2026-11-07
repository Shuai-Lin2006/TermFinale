

## 核心考点：实数完备性与数列极限
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 1 页

本章是整门课的**地基**。极限的 $\varepsilon$-$N$ 语言一旦立住，后面连续、微分、积分才有落脚点。本讲按概览处理：只抓主线、必考点与范围边界，不逐页展开。请把下面三块吃透——极限定义与性质、子列与收敛的关系、实数不等式工具。



### 1.1 极限定义与基本性质

> **定义**：$\{x_n\}$ 收敛到 $x$，指对任意 $\varepsilon>0$，存在 $N$，当 $n\geqslant N$ 时 $d(x_n,x)<\varepsilon$，记 $\lim_{n\to\infty}x_n=x$。

围绕这个定义，资料（P.43）收集了五条性质，全部要背。其一，**极限唯一**：若同时收敛到 $x$ 与 $y$，则 $x=y$。证明只用三角不等式：

$$d(x,y)\leqslant d(x_n,x)+d(x_n,y)<2\varepsilon$$

$\varepsilon$ 任意，故 $d(x,y)=0$。其二，**改动有限项不改变极限**。其三，**收敛数列的子列收敛到同一极限**。其四，**收敛必有界**。其五，极限不是 $x$ 的逆否叙述：存在 $\varepsilon>0$，对任意 $N$，总存在 $n>N$ 使 $d(x_n,x)\geqslant\varepsilon$——这条是考场反证法的起手式（P.43）。

> **易错**：性质四的逆命题不成立。有界不收敛，例如 $x_n=(-1)^n$。别把“有界”当“收敛”用。



### 1.2 子列与收敛的判定

子列是把指标抽成上升序列 $n_1<n_2<\cdots$，令 $y_k=x_{n_k}$（P.43）。核心结论只有一句：**原列收敛 $\Rightarrow$ 子列收敛到同一极限**。反过来，资料给出的实用判据是：**若 Cauchy 列有某个子列收敛，则原列收敛**。这条是本章证明题的高频套路——先证列是 Cauchy 列，再找一个收敛子列，两头一夹即得。

> **易错**：子列收敛推不出原列收敛。$1,-1,1,-1,\cdots$ 的两个子列分别收敛到 $1$ 和 $-1$，原列发散。必须“Cauchy 列 + 子列收敛”两个条件同时在场。



### 1.3 实数不等式与发散举例

实数基本性质落到计算上就是**三角不等式**与**放缩**。资料（P.43）用调和级数演示了放缩的威力：取 $n=2^k$，把项按 $1,2,4,\cdots,2^{k-1}$ 分组，每组和都不小于 $\tfrac12$，于是

$$\sum_{j=1}^{2^k}\frac1j\geqslant 1+\frac{k}{2}$$

$k$ 任意大，部分和超过任意 $M$，故**调和级数发散**。这是“可计算性”思想的样板：分组后求和变容易（P.43）。

**例 1-1**
题：证明 $\lim_{n\to\infty}\dfrac{1}{n}=0$。
解：任给 $\varepsilon>0$，取 $N=\left[\dfrac1\varepsilon\right]+1$，当 $n\geqslant N$ 时

$$\left|\frac1n-0\right|=\frac1n<\varepsilon$$

所以极限为 $0$。



### 1.4 易错与考场用法

考场三步走：**先写 $\varepsilon$-$N$ 定义，再用三角不等式放缩，最后令 $\varepsilon$ 任意**。证明唯一性、有界性都套这个模子。遇到“子列”题，先问自己：原列是不是 Cauchy 列？有没有现成的收敛子列？两问都答上，结论自然落地。

> **易错**：写 $\varepsilon$-$N$ 证明时，$N$ 必须**先于** $n$ 选定，不能反过来“对每个 $n$ 找 $N$”。顺序颠倒，整段证明作废。

P.1 为封面页，仅含书名与作者信息，无新增考点；P.85 讨论 Basel 问题与 $\sin$ 的乘积展开，属后续章节内容，本章不展开；P.126 为作业题页，仅含习题清单，无新增考点。

---



## 核心考点：第2部分 · 第127–252页

> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 127 页

本章是全书概览性质的一章，主线有两条：一是从 Riemann 和的收敛性出发建立定积分并证明其线性与连续性，二是引入原函数、微积分基本工具，最后把微分方程的解归结为不动点定理。下面只抓必考要点、公式卡与解题套路，不展开冗长推导。



### 2.1 定积分的定义与基本性质

对 $[a,b]$ 上的函数 $f$，用分割对应的[[Riemann 和 | 用矩形面积近似曲线下面积的求和]] $S_n$ 逼近积分。资料指出：证明 $\{S_n\}_{n\geqslant 1}$ 收敛后，用 $\lim_{n\to\infty} S_n$ 记作 $\int_a^b f$（P.127）。进一步，映射

$$f \mapsto \int_a^b f$$

是从 $C[a,b]$ 到 $\mathbb{R}$ 的[[线性映射 | 满足可加与齐次]]，并且在距离 $d_\infty$ 下是[[连续映射 | 输入函数微小扰动则积分值也微小变化]]（P.127）。

> **定义**：若 $f$ 为正函数，则 $\int_a^b f$ 表示 $f$ 图像下的面积（P.127）。

> **易错**：即便 $f(x)=x^m$ 这样简单的函数，直接算 $\int_a^b f$ 都很复杂，本章不要求硬算，重点是掌握性质与后续计算工具（P.127）。

该页仅含图示/无新增考点（P.128）。



### 2.2 原函数与积分基本定理

设 $f$ 定义在区间 $I$ 上，若存在 $F$ 使 $F$ 可微且 $F'=f$，则称 $F$ 是 $f$ 的[[原函数 | 求导后等于 f 的函数]]（P.211）。若 $F$ 是一个原函数，则 $f$ 的全部原函数为 $F+c$，$c\in\mathbb{R}$，因为导数恒为零当且仅当函数为常值（P.211）。

> **命题 126**：对 $f\in R(I)$，定义 $F(x)=\int_a^x f$，则 $F$ 在 $I=[a,b]$ 上连续；若 $f$ 在 $x_0$ 右连续，则 $F$ 的右导数存在且等于 $f(x_0^+)$。特别当 $f\in C(I)$ 时，$F(x)=\int_a^x f(y)\,dy$ 是 $f$ 的原函数（P.211）。

证明思路只用一步：设 $|f|\leqslant M$，则 $|F(x-h)-F(x)|\leqslant |h|\cdot M=O(h)$，故连续（P.211）。



### 2.3 积分存在的等价刻画

资料给出积分理论的关键链条：上下极限相等、阶梯函数逼近与可积性互相等价。核心结论是：对任意 $\varepsilon>0$，存在阶梯函数 $\underline{f}\leqslant f\leqslant \overline{f}$ 使 $\int_a^b \overline{f}-\int_a^b \underline{f}<\varepsilon$，则 $f\in R(I)$，且

$$\int_a^b \underline{f}\leqslant \int_a^b f\leqslant \int_a^b \overline{f}$$

（P.211）。这条是判定可积与估算积分值的通用工具。



### 2.4 微分方程与不动点

对初值问题 $x(t)=x(t_0)+\int_{t_0}^t f(x(\tau),\tau)\,d\tau$，在 $d_\infty$ 下验证压缩条件

$$d_\infty\big(T(x),T(y)\big)\leqslant C\delta\, d_\infty\big(x,y\big)$$

只要 $\delta C\leqslant 1$，由[[不动点定理 | 压缩映射必有唯一不动点]]得唯一解 $x(t)$，且 $x'(t)=f(x(t),t)$（P.252）。二阶方程 $x''=f(x',x,t)$ 可通过令 $X=(x,x')^T$ 化为一阶系统，仍局部有解（P.252）。

**例 2-1**
题：验证 $f''+f=0$ 在初值 $(f(0),f'(0))=(0,1)$ 下的解。
解：化为一阶系统 $X'=f(X,t)$，由不动点定理局部唯一解存在；代入验证 $\sin x$ 满足方程与初值，故解为 $\sin x$（P.252）。



### 2.5 易错与考场用法

> **易错**：原函数族必须写 $F+c$，漏掉常数 $c$ 直接扣分（P.211）。

> **易错**：命题 126 中“右连续”只保证右导数，不要误写成双侧可导（P.211）。

考场三步套路：先判可积（用阶梯函数逼近或上下极限相等），再用命题 126 求原函数，最后用不动点定理处理微分方程初值问题。该页仅含图示/无新增考点（P.129–P.134）。

---



## 核心考点：第3部分 · 第253–378页
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 253 页

本章是全书概览性质的一章，主线从 Newton 力学与万有引力出发建立行星运动的常微分方程模型，随后转入多元微分学中方向导数与可微性的讨论，最后以反函数定理与隐函数定理的作业题收束。下面只抓必考主线与范围边界，不逐页展开。



### 3.1 行星运动的数学建模

Newton 三定律与万有引力定律是本章建模的出发点：惯性定律、$F=ma$、作用力与反作用力，以及

$$F = G\frac{m_1 m_2}{r^2},\qquad G = 6.67\times 10^{-11}\,\mathrm{N\cdot m^2/kg^2}.$$

建模时作两个理想化假设：把太阳与行星视为质点（半径相对轨道尺度可忽略）；忽略行星间引力（太阳质量占太阳系 99.8% 以上）。取太阳在原点，行星位置 $x(t)\in\mathbb{R}^3$，由第二定律得

$$x''(t) = -GM\,\frac{x(t)}{r^3},\qquad r(t)=|x(t)|.$$

关键结论：方程与行星质量 $m$ 无关，只依赖太阳质量 $M$。适当选坐标系使 $x(0)=x_0$、$x'(0)=v_0$ 落在平面 $z=0$ 上，则第三坐标满足 $z''(t)=-\frac{GM}{r^3}z(t)$，初值 $(z(0),z'(0))=(0,0)$（P.253）。

> **易错**：受力方向是 $-\frac{x(t)}{r}$，即指向太阳的单位向量，符号写反是常见失分点（P.253）。



### 3.2 方向导数与可微性

对 $v,w\in\mathbb{R}^n$，希望有 $(\nabla_{v+w}f)(x_0)=(\nabla_v f)(x_0)+(\nabla_w f)(x_0)$，但这仅靠各方向导数存在不够，需可微性条件（P.337）。两个基本例子：只依赖 $x$ 的函数 $f(x,y)=f(x)$ 有 $\frac{\partial f}{\partial y}\equiv 0$；而

$$f(x,y)=\frac{xy}{x^2+y^2}\ (x,y)\neq(0,0),\quad f(0,0)=0$$

在原点两个偏导均为 $0$，但当 $v_1v_2\neq 0$ 时 $\nabla_v f(0)$ 不存在——偏导存在不保证其他方向导数存在（P.337）。

> **定义**：方向导数本质是一维导数；曲线 $\gamma:I\to\mathbb{R}^n$ 的 $\gamma'(0)$ 称为 $\gamma$ 在 $\gamma(0)$ 处的切向量，不同点的切向量互不相关（P.337）。



### 3.3 反函数定理相关题型

作业主线围绕反函数定理：$f(x)=x+x^2\sin(\pi/x)$ 在 $0$ 处 $df(0)\neq 0$ 但邻域内非单射，用于对照反函数定理缺失的条件；$f(x,y)=(e^x\cos y,e^x\sin y)$ 处处满足定理要求却既非单射也非满射；以及 $|f(x)-f(y)|\geqslant a|x-y|$ 时 $f$ 为 $C^1$ 微分同胚（定理只给局部同胚）（P.378）。



### 3.4 振荡积分估计（选学边界）

P.295 一组题：$h$ 在端点附近恒为 $0$ 时 $\int h\cdot Lg=\frac{1}{\lambda}\int g\cdot Mh$；$|I(\lambda)|\leqslant c_n/\lambda^n$；$|\varphi'|\geqslant\delta$ 时 $\left|\int e^{i\lambda\varphi}\right|\leqslant C_1/(\lambda\delta)$；$|\varphi''|\geqslant 1$ 时存在唯一 $c$ 使 $|\varphi'(c)|=\inf|\varphi'|$ 且 $|\varphi'(x)|\geqslant|x-c|$，进而 $\left|\int e^{i\lambda\varphi}\right|\leqslant C_2/\lambda$ 及带 $|f'|$ 的版本。此部分属提高内容，期末按常规难度一般不深考（P.295）。

> **易错**：P.254–P.260 该页仅含图示/无新增考点，复习时不必逐页死抠。

---



## 核心考点：第4部分 · 第379–504页
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 379 页

这一部分的主线是**从局部微分同胚走向整体微分同胚**，并顺带把测度论的基本框架搭起来。前半段（P.379–P.386）用压缩映像、反函数定理、Jacobi 矩阵可逆性这些工具，判断一个映射能否“局部可逆、整体也漂亮”；后半段（P.421、P.463、P.504）转入 Lebesgue 测度与积分，讲测度的唯一性、平移不变性以及控制收敛定理的典型题型。下面按“必背要点—公式卡—三步套路”压缩呈现，概览性质，不逐页精讲。



### 4.1 必背要点（3~5 条）

**要点一：压缩映像判据。** 对任意 $(a,b)\in\mathbb{R}^2$，映射 $g_{a,b}(x,y)=(a-f(y),\,b-f(x))$ 是压缩映像，这是证明 $F$ 为微分同胚的关键一步（P.379）。记住：压缩映像定理保证不动点存在且唯一，这是整体可逆性的落脚点。

**要点二：局部微分同胚的判定。** 对 $F(x,y)=(x+y,\,f(x)+g(y))$，若对任意 $x,y$ 有 $f'(x)\neq g'(y)$，则 $F$ 的像 $U=F(\mathbb{R}^2)$ 是开集，且 $F:\mathbb{R}^2\to U$ 是微分同胚（P.379）。核心条件就是**导数不相等**，它保证 Jacobi 行列式非零。

**要点三：隐函数定理的局部形式。** 在 $\Omega=\{x>0\}$ 上定义 $F(x,y)=y-y_0+p(x,y)+p_0\frac{x}{x_0}-1$，则在 $p_0$ 点附近存在开邻域 $U$ 与 $C^1$ 函数 $\phi$，使 $F(x,y)=0\iff y=\phi(x)$（P.379）。这是隐函数定理的标准应用场景。

**要点四：Jacobi 矩阵可逆与光滑单射。** 对 $\varphi(x,y)=(\sin(y-x),\,\sin(x-y))$，它是光滑单射，且在任意点 Jacobi 矩阵可逆；由此可对每点找到开集 $U,V$ 使 $\varphi:U\to V$ 是光滑微分同胚，最终证明 $\varphi$ 整体是光滑微分同胚、像为闭集（P.379）。

**要点五：Lebesgue 测度的唯一性与平移不变性。** 在 $\mathbb{R}^n$ 的 Borel 代数上存在唯一测度 $m$，使方块 $C=I_1\times\cdots\times I_n$ 满足 $m(C)=|I_1|\times\cdots\times |I_n|$；平移 $\tau_v(x)=x+v$ 本质上刻画了 Lebesgue 测度（P.463）。控制收敛定理是 P.504 明确标注“必须掌握”的内容。



### 4.2 公式卡

| 公式 | 符号含义 | 适用条件 |
|---|---|---|
| $g_{a,b}(x,y)=(a-f(y),\,b-f(x))$ | 压缩映像构造 | 用于证明 $F$ 微分同胚（P.379） |
| $F(x,y)=(x+y,\,f(x)+g(y))$ | 整体微分同胚映射 | 需 $f'(x)\neq g'(y)$（P.379） |
| $\det \mathrm{Jac}(\varphi)(x,y)\neq 0$ | Jacobi 行列式非零 | 保证局部可逆（P.379） |
| $m(C)=\prod_{i=1}^n |I_i|$ | 方块测度 | Lebesgue 测度定义（P.463） |
| $\int_X f\,d\mu=\int_Y \tilde f\,d\mu_Y$ | 换空间积分 | $f$ 在 $Y$ 上可积当且仅当 $\tilde f$ 在 $X$ 上可积（P.504） |



### 4.3 三步解题套路

**第一步：先验可逆性。** 拿到映射先算 Jacobi 矩阵，检查行列式是否处处非零；若条件形如 $f'(x)\neq g'(y)$，直接引用即得局部微分同胚（P.379）。

**第二步：再证整体性。** 局部可逆不够，要用压缩映像定理（构造 $g_{a,b}$）或证明单射+像为闭集，把局部结论抬到整体（P.379）。

**第三步：测度与积分题套定理。** 遇到积分极限交换，先判断是否满足控制收敛定理条件（可积控制函数）；遇到方块测度直接用乘积公式；遇到换空间积分用 P.504 的等式（P.463、P.504）。



### 4.4 易错与考场用法

> **易错**：$f'(x)\neq g'(y)$ 是**对任意** $x,y$ 成立，不是存在某点；漏掉“任意”二字，整体微分同胚的结论就垮了（P.379）。

> **易错**：Jacobi 矩阵处处可逆只给**局部**微分同胚，整体单射与像的闭性必须单独证，别混为一谈（P.379）。

> **易错**：Fatou 引理中不等式未必取等号，P.504 的 A6 就是让你构造严格小于的反例，考场上别想当然写等号（P.504）。

P.380–P.386 各页在本批资料中未给出可用正文，仅作范围衔接；P.421 为凸函数估计的辅助推导，属前后章过渡内容，此处不展开。

---



## 核心考点：第5部分 · 第505–630页
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 505 页

本章是全书概览性质的一章，主线围绕**卷积、Fourier 变换与 Fourier 级数**展开，从可积函数的周期化、卷积的连续性，一路推进到圆周 $\mathbb{T}$ 上的 $L^2$ 理论与 Hilbert 基。它承接前一部分的测度与积分工具，又为下一章的进一步展开铺路。下面只抓主线与必考点，不逐页精讲。



### 5.1 周期化与卷积的定义

先看周期化。设 $f$ 是 $\mathbb{R}$ 上的可积函数，令

$$\tilde f(x)=\sum_{k\in\mathbb{Z}} f(x+k),\quad x\in[0,1].$$

要证明 $\tilde f$ 良定义、可测且在 $[0,1]$ 上可积，并进一步证明

$$\int_{[0,1]}\tilde f(x)\,dx=\int_{\mathbb{R}} f(x)\,dx.$$

这是把全直线上的积分“折叠”到一个周期上的标准手法（P.505）。

> **定义**：对 $f$ 可积、$g$ 有界连续，[[卷积 | 把两个函数“滑动相乘再积分”得到的新函数]]定义为

$$f*g(x)=\int_{\mathbb{R}} f(x-y)g(y)\,dy=\int_{\mathbb{R}} f(y)g(x-y)\,dy.$$

结论是：$f*g$ 定义了 $\mathbb{R}$ 上一个**有界连续**函数（P.505）。若 $g$ 连续可微且 $g,g'$ 均有界，则 $f*g$ 连续可微，且 $(f*g)'=f*g'$（P.505）。



### 5.2 有限测度的 Fourier 变换

在 $\mathbb{R}$ 上取定 Borel-代数。若 $\mu$ 是有限测度（$\mu(\mathbb{R})<\infty$），则

$$\hat\mu(\xi)=\int_{\mathbb{R}} e^{-ix\xi}\,d\mu(x)$$

定义了 $\mathbb{R}$ 上一个**连续有界**函数，称为该有限测度的 [[Fourier 变换 | 把测度映成频率空间里的函数]]（P.505）。这是后续 Fourier 分析的起点。



### 5.3 散度、旋度与散度定理

进入向量场部分。对光滑向量场 $X$，[[散度 | 各分量偏导之和]]与[[旋度 | 由偏导差构成的向量场]]定义为

$$\operatorname{div}X=\sum_{k=1}^{n}\frac{\partial X_k}{\partial x_k},\qquad \operatorname{curl}X=\nabla\times X.$$

$n=3$ 与 $n=2$ 时旋度分别写成向量场与函数形式（P.589）。这些量的几何意义要靠 Stokes 公式才能读出，但先记住一批代数恒等式，例如

$$\nabla\times(\nabla\varphi)=0,\qquad \nabla\cdot(\nabla\times X)=0,\qquad \triangle\varphi=\nabla\cdot(\nabla\varphi),$$

其中 $\triangle$ 是 [[Laplace 算子 | 二阶偏导之和]]（P.589）。这些等式均可直接计算验证。

> **定理（散度定理）**：设 $\Omega\subset\mathbb{R}^n$ 是有界光滑带边区域，$\nu$ 为 $\partial\Omega$ 的单位外法向量，$d\sigma$ 为边界子流形测度，则对 $C^1$ 向量场 $X$，

$$\int_{\Omega}\operatorname{div}X\,dx=\int_{\partial\Omega}\langle X,\nu\rangle\,d\sigma.$$

（P.589）



### 5.4 圆周上的 Fourier 级数

最后转到圆周 $\mathbb{T}$。以 $2\pi$ 为周期的连续函数与 $\mathbb{T}$ 上的连续函数可视为同一对象，用 $\theta\mapsto e^{i\theta}$ 参数化，并约定测度 $\mu=\frac{dx}{2\pi}$，使 $\mu(\mathbb{T})=1$（P.630）。相应地有 $C^1(\mathbb{T}),C^\infty(\mathbb{T}),L^1(\mathbb{T}),L^2(\mathbb{T}),L^\infty(\mathbb{T})$ 等空间。

> **引理**：对 $p=1,2,\infty$，$C^\infty(\mathbb{T})\subset L^p(\mathbb{T})$ 是稠密子空间（P.630）。证明思路是把卷积推广到 $\mathbb{T}$ 上，用周期延拓的磨光核 $\chi_\varepsilon$ 作卷积逼近。

核心结论是：在 $L^2\!\left([0,2\pi],\frac{dx}{2\pi}\right)$ 中，内积为

$$\langle f,g\rangle=\int_0^{2\pi} f(x)\overline{g(x)}\,\frac{dx}{2\pi},$$

则函数族 $\{e^{ikx}\}_{k\in\mathbb{Z}}$ 是 [[Hilbert 基 | 一组正交完备基]]（P.630）。这是 Fourier 级数展开的理论基石。



### 5.5 易错与考场用法

> **易错**：周期化公式中求和指标 $k\in\mathbb{Z}$ 覆盖全部整数，漏掉负半轴是常见错误；散度定理要求 $\Omega$ 有界光滑带边、$X$ 为 $C^1$，条件不满足不能硬套（P.589）。

考场套路三步：先判断对象是函数、测度还是向量场；再对号入座选公式（卷积、Fourier 变换、散度定理）；最后核对可积性、有界性、光滑性等适用条件。本章为概览，逐页细节请回看对应页码。

---



## 核心考点：第6部分 · 第631–756页
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 631 页

本章是**概览**性质，横跨傅里叶级数的完备性、球面调和函数、分布与卷积三块内容，主线是“正交系 → 稠密性 → 基”这条逻辑链在不同空间上的反复运用。下面只抓必考骨架，不逐页展开。



### 6.1 傅里叶级数的完备性

核心结论：$\{e^{ikx}\}_{k\in\mathbb{Z}}$ 在 $L^2([0,2\pi])$ 中构成[[正交系 | 两两内积为零]]，且张成的空间稠密。

> **定义**：内积定义为
> $$\langle e^{ikx}, e^{i\ell x}\rangle=\frac{1}{2\pi}\int_0^{2\pi}e^{i(k-\ell)x}\,dx=\delta_\ell^k.$$

证明稠密性的套路是“垂直于稠密子空间则为零”：设 $f\perp V$，用 Weierstrass-Stone 定理把连续函数 $\varphi$ 用三角级数 $S$ 逼近，$\|S-\varphi\|_{L^\infty}\le\varepsilon$，于是

$$|\langle f,\varphi\rangle|\le\varepsilon\|f\|_{L^2}\|\mathbf{1}\|_{L^2}\to 0.$$

再由 $C([0,2\pi])$ 在 $L^2$ 稠密得 $f=0$（P.631）。**这一步是本章证明题的模板，务必背熟。**



### 6.2 球面调和函数

在 $S^2$ 上构造 $Y_m^\ell=C_{m,\ell}Z_m^\ell(\vartheta)e^{im\varphi}$，负 $m$ 用 $Y_m^\ell=\overline{Y_{-m}^\ell}$ 定义（P.673）。必记三条恒等式：

$$-\triangle_{S^2}Y_m^\ell=\ell(\ell+1)Y_m^\ell,\qquad J_3Y_m^\ell=mY_m^\ell.$$

以及升降算子的作用 $J_\pm Y_m^\ell=\sqrt{(\ell\mp m)(\ell\pm m+1)}\,Y_{m\pm1}^\ell$（P.673）。结论：$\{Y_m^\ell\}$ 是 $L^2(S^2)$ 的[[Hilbert 基 | 完备正交系]]，核心思想是 $-\triangle_{S^2}$ 与 $J_3$ 交换、可同时对角化。



### 6.3 分布与卷积

若 $T_f=0$ 作为分布，则 $f=0$ 几乎处处。证法：取 $\varphi_K=\frac{f}{|f|}\mathbf{1}_K$，用磨光 $\chi_\varepsilon*\varphi_K\in\mathcal{D}(\Omega)$ 代入，令 $\varepsilon\to0$ 得 $\int_K|f|=0$（P.715）。卷积交换律 $c_1*c_2=c_2*c_1$ 对 $c_1,c_2\in\mathcal{E}'(\mathbb{R}^n)$ 成立，证明靠磨光逼近 $c_{1,\varepsilon}=c_1*\chi_\varepsilon\to c_1$ 再取极限（P.756）。



### 6.4 易错与考场用法

> **易错**：稠密性证明中“$f\perp V$ 推出 $f\perp C$”依赖 $S$ 的 $L^\infty$ 逼近，不能直接说 $V$ 稠密；磨光核 $\chi_\varepsilon$ 的支集必须落在 $\Omega$ 内，靠紧性保证。

三步套路：①验证正交归一；②假设垂直、用稠密子空间逼近到零；③由稠密性得 $f=0$。三块内容共用这一条主线，考场遇证明先套此框架。

（P.632–P.638 为上述内容的展开与习题，主线不超出以上要点；该段页码仅含推导细节与练习，无新增考点。）

---



## 核心考点：第7部分 · 第757–882页
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 757 页

本章是全书**概览**性质的一章，横跨分布卷积的连续性、$L^2$ 上的 Fourier 变换与 Plancherel 公式、Poisson 求和公式，直到 Sobolev 空间 $H^1(\Omega)$ 的逼近与边界空间 $H^2(\partial\Omega)$ 的定义。范围很宽，但主线只有一条：**先建立分布与 $L^2$ 上的基本运算（卷积、Fourier 变换），再用它们刻画 Sobolev 空间**。下面只抓必考骨架，逐页精讲不在本章任务内。



### 7.1 分布卷积的连续性与结合律

本节要解决的核心问题是：当两个分布序列在 $\mathcal{D}'$ 意义下收敛时，卷积运算是否保持连续？答案是：只要其中一个分量具有紧支集，卷积对**每一个分量分别连续**。

> **定义**：设 $\{c_k\}\subset\mathcal{E}'(\mathbb{R}^n)$ 且支集含于同一紧集 $K$，$\{u_k\}\subset\mathcal{D}'(\mathbb{R}^n)$。若 $c_k\xrightarrow{\mathcal{D}'}c$，$u_k\xrightarrow{\mathcal{D}'}u$，则在分布意义下
> $$u_k*c\xrightarrow{\mathcal{D}'}u*c,\qquad u*c_k\xrightarrow{\mathcal{D}'}u*c.$$

证明的关键技巧是**用试验函数对偶**：$\langle u_k*c,\varphi\rangle=\langle u_k,\check{c}*\varphi\rangle$，而 $\check{c}*\varphi\in\mathcal{D}$，于是极限直接由 $u_k$ 的收敛得到（P.757）。第二个极限需要引入紧支集光滑函数 $\psi$ 在 $\operatorname{supp}(\varphi)-K$ 上恒等于 $1$，把 $\check{c}_k*\varphi$ 的支集“锁住”，这是常用手法（P.757）。

> **易错**：该定理只保证对**每个分量**连续，不是对两个分量同时连续。直观上可把卷积 $\mathcal{D}'\times\mathcal{E}'\to\mathcal{D}'$ 看作由其在 $C^\infty\times C_0^\infty$ 上的限制决定（P.757）。

由此立即得到结合律：对 $c_1,c_2\in\mathcal{E}'$，$u\in\mathcal{D}'$，
$$(u*c_1)*c_2=u*(c_1*c_2).$$
（P.757）



### 7.2 $L^2$ 上的 Fourier 变换与 Plancherel 公式

$L^1$ 上的 Fourier 积分对 $L^2$ 函数未必有意义，因此必须在 $L^2$ 意义下重新定义变换，并证明它是等距同构。

> **定理**：可定义 Fourier 变换 $\mathcal{F}:L^2(\mathbb{R}^n)\to L^2(\mathbb{R}^n)$，使得
> $$(2\pi)^{-\frac{n}{2}}\mathcal{F}:L^2(\mathbb{R}^n)\longrightarrow L^2(\mathbb{R}^n)$$
> 是等距同构。特别对 $f\in L^1\cap L^2$，
> $$\|\hat{f}\|_{L^2}^2=(2\pi)^n\|f\|_{L^2}^2.$$

通过极化得到内积形式 $(\hat{f},\hat{g})_{L^2}=(2\pi)^n(f,g)_{L^2}$（P.799）。证明思路：先对 $C_0^\infty$ 成立，再用 $C_0^\infty$ 逼近一般 $f\in L^2$（P.799）。

> **易错**：$L^2$ 意义下的变换记作 $\mathcal{F}_2$，$L^1$ 积分定义的记作 $\mathcal{F}_1$；对 $f\in L^1\cap L^2$ 有 $\mathcal{F}_1(f)=\mathcal{F}_2(f)$，但一般 $L^2$ 函数不能用积分写（P.799）。

典型例子：$u(x)=(1+|x|)^{-\alpha}$（$\tfrac12<\alpha\le 1$）不在 $L^1$，需用截断 $u_n=u\cdot\mathbf{1}_{|x|\le n}$ 在 $L^2$ 中逼近再取极限（P.799）。配套练习：$\widehat{\hat{f}}=\check{f}$，即 $\mathcal{F}_2(f)=\check{f}$（P.799）。



### 7.3 Poisson 求和公式与 Sobolev 边界空间

Poisson 求和把周期求和与 Fourier 变换联系起来：对每个 $\varphi\in\mathcal{S}(\mathbb{R})$，
$$\sum_{k\in\mathbb{Z}}f(2\pi k)=\frac{1}{2\pi}\sum_{k\in\mathbb{Z}}\hat{f}(k).$$
（P.841）此公式的推导依赖 $W_\lambda$ 所满足的分布方程组 $(\delta_\lambda-\delta_0)*u=0$ 与 $(e^{\frac{2\pi i x}{\lambda}}-1)u=0$，并证明其缓增解必为 $W_\lambda$ 的倍数，再算出 $\widehat{W_\lambda}=C_\lambda W_\lambda$ 中的常数 $C_\lambda$（P.841）。

转向 Sobolev 空间：$H^1(\Omega)$ 可用全空间光滑函数逼近——对任意 $u\in H^1(\Omega)$，存在 $\{\varphi_k\}\subset C_0^\infty(\mathbb{R}^n)$ 使 $\varphi_k|_\Omega\to u$ 于 $H^1(\Omega)$（P.882）。证明只用延拓算子 $\mathrm{Ext}(u)$ 与全空间逼近（P.882）。

边界空间 $H^2(\partial\Omega)$ 有两种等价定义：其一是局部覆盖加单位分解，用 $\|u\|^2_{H^2(\partial\Omega),\mathcal{U}}=\sum_j\|u_j\circ\phi_j^{-1}\|^2_{H^2(\mathbb{R}^{n-1})}$，不同覆盖给出等价范数（P.882）；其二是当 $0<s<1$ 时用
$$\|u\|^2_{H^s(\mathbb{R}^n)}\approx\|u\|^2_{L^2}+\iint_{\mathbb{R}^n\times\mathbb{R}^n}\frac{|u(x)-u(y)|^2}{|x-y|^{n+2s}}\,dx\,dy.$$
（P.882）

> **易错**：$H^2(\partial\Omega)$ 的范数定义依赖覆盖与单位分解的选取，必须证明等价性才能谈收敛（P.882）。



### 7.4 考场用法与边界提醒

本章为**概览**，考试重心在：卷积连续性定理的**对偶计算**、Plancherel 等距公式的**常数 $(2\pi)^n$**、Poisson 求和的**系数 $\frac{1}{2\pi}$**、以及 $H^1$ 逼近与 $H^2(\partial\Omega)$ 两种范数定义。P.758–P.764 在本批资料中未给出可用正文，**该页仅含图示/无新增考点**，复习时不必在此纠缠。

---



## 核心考点：第8部分 · 第883–1001页
> 📌 出处：《Analysis123清华大学于品数学分析讲义.pdf》第 883 页

本章是全书收尾部分，主线有两条：一是分数阶 Sobolev 空间 $H^2(\partial\Omega)$ 在边界上的定义与范数等价性（P.883）；二是 Laplace 算子特征值的变分刻画与区域单调性（P.922），最后落到分布意义下 Klein–Gordon 方程与正则次数的综合练习（P.1001）。注意：本章为**概览**，只抓必考主线，不逐页展开。



### 8.1 边界上的分数阶 Sobolev 空间

> **定义**：设 $d\sigma$ 为 $\partial\Omega$ 上的曲面测度。若 $u\in L^2(\partial\Omega)$ 且
> $$\iint_{\partial\Omega\times\partial\Omega}\frac{|u(x)-u(y)|^2}{|x-y|^{n}}\,d\sigma(x)d\sigma(y)<\infty,$$
> 则称 $u\in H^2(\partial\Omega)$，并定义
> $$\lVert u\rVert_{H^2(\partial\Omega)}^2=\lVert u\rVert_{L^2(\Omega)}^2+\iint_{\partial\Omega\times\partial\Omega}\frac{|u(x)-u(y)|^2}{|x-y|^{n}}\,d\sigma(x)d\sigma(y).$$

这个范数满足三角不等式，故确为范数。关键结论：对任意 $\delta>0$，把积分核截断到 $|x-y|<\delta$ 后得到的范数与原范数**等价**，两者只差一个约为 $\delta^{-(n+1)}$ 的常数（P.883）。证明思路是用开覆盖 $\{U\}$ 使 $\operatorname{diam}(U)<\tfrac12\delta$，配合截断函数 $\chi_j$ 与 Lagrange 中值定理控制 $|\chi_j(x)-\chi_j(y)|\le C|x-y|$，把交叉项化为 $\int|x-y|^{n-2}|u(y)|^2d\sigma$ 型积分，再用练习中的一致有界性 $\int_{\partial\Omega}|x-y|^{n-2}d\sigma(x)\le C$ 收尾（P.883）。

> **易错**：截断函数 $\chi_j$ 光滑、$u$ 不光滑，中值定理只能用在 $\chi_j$ 上，不能对 $u$ 用。



### 8.2 特征值的变分刻画与区域单调性

设 $\lambda_k$ 为 Laplace 算子在 $H_0^1(\Omega)$ 上的第 $k$ 个特征值，$R(u)=\lVert\nabla u\rVert^2_{L^2}/\lVert u\rVert^2_{L^2}$ 为 Rayleigh 商。核心结论是 $\lambda_k$ 可用 Grassmann 流形 $\mathrm{Gr}_k(H)$ 上的量 $\nu(Q)$ 刻画：

$$\lambda_k=\inf_{Q\in\mathrm{Gr}_k(H)}\nu(Q),$$

且 $\nu(Q)=\lambda_k$ 可由 $\varphi_k$ 取到（P.922）。反向不等式依赖线性代数事实：每个 $Q\in\mathrm{Gr}_k$ 中存在非零 $u\perp\varphi_1,\dots,\varphi_{k-1}$，从而 $\mu(Q)\ge R(u)\ge\lambda_k$（P.922）。

> **注记**：由该刻画得 $\lVert\nabla u\rVert^2_{L^2}\ge\lambda_1\lVert u\rVert^2_{L^2}$，即 $\lambda_1$ 是 Poincaré 不等式的最佳常数（P.922）。

**推论（区域单调性）**：若 $\Omega_1\subset\Omega_2$，则对每个 $k\ge1$ 有 $\lambda_k(\Omega_1)\ge\lambda_k(\Omega_2)$（P.922）。证明用零延拓嵌入 $\iota:H_0^1(\Omega_1)\to H_0^1(\Omega_2)$，把 $\lambda_k(\Omega_1)$ 的上确界搬到 $\Omega_2$ 中计算，得 $\lambda_k(\Omega_1)\ge\nu(\iota(\varphi_1)\wedge\cdots\wedge\iota(\varphi_k))\ge\lambda_k(\Omega_2)$（P.922）。



### 8.3 分布框架下的振荡积分与正则次数

对紧支分布 $u\in\mathcal{E}'(\mathbb{R}^n)$，若在锥型开集 $\Gamma(\eta_0,\alpha_0)$ 上 $|\hat u(\xi)|\le C_N(1+|\xi|)^{-N}$，则振荡积分 $I(\xi)=\langle u,e^{-i\phi(x,\xi)}a(x,\xi)\rangle$ 需用逼近 $u_\varepsilon=\mathcal{F}^{-1}(\chi_\varepsilon\hat u)$ 定义，并借 $\psi\in C_0^\infty$、$\psi|_K\equiv1$ 给出积分表示（P.962）。这是把分布配对化为绝对收敛积分的标准套路。

> **定义（正则次数）**：若 $\lim_{\varepsilon\to0}\langle v,\varphi(x/\varepsilon)\rangle=0$ 对一切 $\varphi\in\mathcal{D}$ 成立，称 $v$ 在 $0$ 处正则；使 $x^n v$ 正则而 $x^{n-1}v$ 不正则的 $n$ 称为正则次数（P.1001）。四条必记结论：$L^1_{\mathrm{loc}}$ 函数正则次数为 $0$；正则次数 $n$ 时 $xv$ 为 $n-1$；正则次数 $\le n$ 时 $v'$ 为 $\le n+1$；$\delta^{(k)}$ 的正则次数为 $k+1$（P.1001）。



### 8.4 易错与考场用法

> **易错**：区域单调性方向是**小区域特征值大**，$\lambda_k(\Omega_1)\ge\lambda_k(\Omega_2)$，别写反（P.922）。

考场三步套路：先判空间归属（$H^2(\partial\Omega)$ 还是 $H_0^1$），再套对应范数或变分公式，最后用等价性/单调性把估计化到已知常数。P.1001 的 B26–B31 是综合练习，考场上按“构造 $v_T$ → 验证方程 → 证 $w=0$”的顺序推进即可。

该页仅含图示/无新增考点（P.884–P.890 为上述内容的展开与练习，主线已在 P.883、P.922、P.962、P.1001 覆盖）。

---

## 🎓 结语
同学们，书山有路勤为径。这份讲义里浓缩了期末最核心的考点，老师能帮你们的就到这里了。剩下的路，需要你们自己去考场上走。不要怕，深呼吸，把这几天背的公式稳稳地写在卷子上。祝你们旗开得胜，老师等你们的好消息！