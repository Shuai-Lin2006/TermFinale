# FINAL高数 期末试卷
**满分：100 分**

## 单项选择题（4 题，每题 5 分，共 20 分）

1. 已知方程 $e^{y}+xy=e$ 确定隐函数 $y=y(x)$，则曲线在点 $(0,1)$ 处的切线斜率为（ ）
A. $-e$
B. $-\dfrac{1}{e}$
C. $\dfrac{1}{e}$
D. $e$
【考点：隐函数求导】

2. 设 $y=\dfrac{1}{x+2}$，则其 $n$ 阶导数 $y^{(n)}=$（ ）
A. $\dfrac{(-1)^{n}\,n!}{(x+2)^{n+1}}$
B. $\dfrac{(-1)^{n-1}\,n!}{(x+2)^{n+1}}$
C. $\dfrac{n!}{(x+2)^{n+1}}$
D. $\dfrac{(-1)^{n}\,(n-1)!}{(x+2)^{n+1}}$
【考点：高阶导数间接法】

3. 设由参数方程 $\begin{cases}x=t^{2}+1\\ y=t^{3}-t\end{cases}$ 确定函数 $y=y(x)$，则 $\dfrac{d^{2}y}{dx^{2}}=$（ ）
A. $\dfrac{3t^{2}-1}{2t}$
B. $\dfrac{3t^{2}+1}{4t^{3}}$
C. $\dfrac{3t^{2}+1}{2t}$
D. $\dfrac{3t^{2}+1}{4t^{2}}$
【考点：参数方程二阶导】

4. 一气球从离开观察员 $500\text{ m}$ 处离地面铅直上升，其速率为 $140\text{ m/min}$。当气球高度为 $500\text{ m}$ 时，观察员视线的仰角增加率约为（ ）
A. $0.14\text{ rad/min}$
B. $0.28\text{ rad/min}$
C. $0.07\text{ rad/min}$
D. $0.20\text{ rad/min}$
【考点：变化率实际问题】

## 填空题（2 题，每题 10 分，共 20 分）

1. 已知曲线 $C$ 的方程为 $x^3+y^3=3xy$，点 $P\!\left(\dfrac{3}{2},\dfrac{3}{2}\right)$ 在曲线 $C$ 上。对方程两边关于 $x$ 求导可得 $y'=\dfrac{y-x^2}{y^2-x}$，则曲线 $C$ 在点 $P$ 处的切线斜率为 ________，切线方程为 ________。【考点：隐函数求导】

2. 一物体沿直线运动，其位移 $s$（单位：m）与时间 $t$（单位：s）由参数方程 $\begin{cases}x=t^2+1\\ y=t^3+t\end{cases}$ 确定（其中 $y$ 表示位移、$x$ 表示时间）。则该物体在 $t=1$ 时的瞬时速度为 ________ m/s，运动的加速度为 ________ m/s²。【考点：参数方程二阶导、变化率实际问题】

## 计算题（2 题，每题 30 分，共 60 分）

1. （30 分）某同学在研究一类幂指型函数的导数时，遇到函数
\[
y=x^{\sin x}\quad(x>0).
\]
为求其导数，他先将等式两边取绝对值，再取对数，得
\[
\ln|y|=\sin x\ln x.
\]

（1）请用隐函数求导法，由上式求出 \(\dfrac{dy}{dx}\)；（12 分）

（2）在（1）的基础上，求该函数的二阶导数 \(\dfrac{d^2y}{dx^2}\)，并将结果整理为只含 \(x\)、\(\sin x\)、\(\cos x\) 的形式；（10 分）

（3）利用（1）的结果，写出曲线 \(y=x^{\sin x}\) 在点 \(x=\dfrac{\pi}{2}\) 处的切线方程，并说明该点处函数值 \(y\) 的取值。（8 分）

【考点：隐函数求导、高阶导数间接法】

2. （30 分）一气球从离开观察员水平距离 \(500\) 米处离地面铅直上升，其速率为 \(1.40\) 米/秒。设气球上升 \(t\) 秒后高度为 \(h(t)\)，观察员视线的仰角为 \(\alpha(t)\)。

（1）建立 \(h\) 与 \(\alpha\) 之间的函数关系式，并说明当 \(h=500\) 米时 \(\sec^2\alpha\) 的值；（10 分）

（2）对关系式两边关于 \(t\) 求导，求出当气球高度 \(h=500\) 米时，观察员视线仰角的增加率 \(\dfrac{d\alpha}{dt}\)（单位：弧度/秒）；（12 分）

（3）若另一时刻气球高度为 \(h=1000\) 米，请判断此时仰角增加率与（2）中结果相比是增大还是减小，并说明理由。（8 分）

【考点：变化率实际问题】

# 答案与解析

## 单项选择题

1. **B**。两边对 $x$ 求导得 $e^y y'+y+xy'=0$，代入 $(0,1)$ 得 $ey'+1=0$，故 $y'=-\dfrac1e$。易错点：忘记 $xy$ 是乘积需用乘积法则。

2. **A**。由 $\dfrac{1}{x+2}=(x+2)^{-1}$ 逐阶求导，符号与阶乘规律为 $\dfrac{(-1)^n n!}{(x+2)^{n+1}}$。易错点：符号 $(-1)^n$ 与 $(-1)^{n-1}$ 混淆。

3. **B**。$\dfrac{dy}{dx}=\dfrac{3t^2-1}{2t}$，再对 $t$ 求导除以 $x'(t)=2t$ 得 $\dfrac{d^2y}{dx^2}=\dfrac{3t^2+1}{4t^3}$。易错点：二阶导须再除以 $x'(t)$，不能直接对一阶导关于 $t$ 求导。

4. **A**。设高度 $h$，$\tan\alpha=\dfrac{h}{500}$，求导得 $\sec^2\alpha\cdot\alpha'=\dfrac{h'}{500}$；$h=500$ 时 $\alpha=\dfrac\pi4$，$\sec^2\alpha=2$，故 $\alpha'=\dfrac{140}{500\times2}=0.14$。易错点：漏掉 $\sec^2\alpha$ 因子。

## 填空题

1. **$-1$；$x+y=3$**。代入 $P$ 得 $y'=\dfrac{\frac32-\frac94}{\frac94-\frac32}=\dfrac{-\frac34}{\frac34}=-1$，切线为 $y-\dfrac32=-(x-\dfrac32)$ 即 $x+y=3$。易错点：代入点坐标时 $x^2$ 与 $x$ 混淆。

2. **$2$；$\dfrac12$**。此处 $x$ 为时间、$y$ 为位移，速度 $v=\dfrac{dy}{dx}=\dfrac{3t^2+1}{2t}$，$t=1$ 时 $v=2$；加速度 $a=\dfrac{d^2y}{dx^2}=\dfrac{(6t)(2t)-(3t^2+1)\cdot2}{4t^3}$，$t=1$ 时 $a=\dfrac{12-8}{4}=1$……按参数方程二阶导公式 $\dfrac{d}{dt}\!\left(\dfrac{3t^2+1}{2t}\right)\Big/2t=\dfrac{3t^2-1}{2t^2}\Big/2t=\dfrac{3t^2-1}{4t^3}$，$t=1$ 得 $\dfrac12$。易错点：加速度是 $y$ 对 $x$ 的二阶导，须再除以 $x'(t)$。

## 计算题

1. **（1）** 由 $\ln|y|=\sin x\ln x$ 两边对 $x$ 求导：$\dfrac{y'}{y}=\cos x\ln x+\dfrac{\sin x}{x}$，故
$$y'=x^{\sin x}\left(\cos x\ln x+\dfrac{\sin x}{x}\right).$$
要点：隐函数求导后回代 $y$。易错点：漏写 $\dfrac{\sin x}{x}$ 项。

**（2）** 记 $u=\cos x\ln x+\dfrac{\sin x}{x}$，则 $y'=y\,u$，$y''=y'u+yu'=y\left(u^2+u'\right)$，其中
$$u'=-\sin x\ln x+\dfrac{\cos x}{x}+\dfrac{x\cos x-\sin x}{x^2}=-\sin x\ln x+\dfrac{2\cos x}{x}-\dfrac{\sin x}{x^2}.$$
故
$$y''=x^{\sin x}\left[\left(\cos x\ln x+\dfrac{\sin x}{x}\right)^2-\sin x\ln x+\dfrac{2\cos x}{x}-\dfrac{\sin x}{x^2}\right].$$
要点：乘积法则与商的求导。易错点：$u'$ 中 $\dfrac{\sin x}{x}$ 求导符号。

**（3）** $x=\dfrac\pi2$ 时 $y=\left(\dfrac\pi2\right)^{\sin(\pi/2)}=\dfrac\pi2$；$y'=\dfrac\pi2\left(0\cdot\ln\dfrac\pi2+\dfrac{1}{\pi/2}\right)=\dfrac\pi2\cdot\dfrac{2}{\pi}=1$。切线：$y-\dfrac\pi2=1\cdot\left(x-\dfrac\pi2\right)$，即 $y=x$。要点：先求点再求斜率。易错点：$\cos\frac\pi2=0$ 使对数项消失。

2. **（1）** $\tan\alpha=\dfrac{h}{500}$，即 $h=500\tan\alpha$。当 $h=500$ 时 $\tan\alpha=1$，$\alpha=\dfrac\pi4$，$\sec^2\alpha=1+\tan^2\alpha=2$。要点：建立仰角与高度关系。易错点：$\sec^2\alpha=1+\tan^2\alpha$ 记错。

**（2）** 对 $h=500\tan\alpha$ 两边关于 $t$ 求导：$\dfrac{dh}{dt}=500\sec^2\alpha\cdot\dfrac{d\alpha}{dt}$。代入 $\dfrac{dh}{dt}=1.40$、$\sec^2\alpha=2$，得
$$\dfrac{d\alpha}{dt}=\dfrac{1.40}{500\times2}=0.0014\ \text{rad/s}.$$
要点：链式法则。易错点：漏乘 $\sec^2\alpha$。

**（3）** 减小。由 $\dfrac{d\alpha}{dt}=\dfrac{1.40}{500\sec^2\alpha}=\dfrac{1.40}{500(1+\tan^2\alpha)}$，$h=1000$ 时 $\tan\alpha=2$，$\sec^2\alpha=5$，$\dfrac{d\alpha}{dt}=\dfrac{1.40}{2500}=0.00056<0.0014$。要点：仰角增大使 $\sec^2\alpha$ 增大、增加率下降。易错点：误认为高度越高增加率越大。