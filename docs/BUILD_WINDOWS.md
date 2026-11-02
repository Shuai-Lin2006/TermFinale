# Windows 构建指南

> 在 **Windows 电脑**上执行（不能在 Mac 上交叉编译出 .exe）。

## 0. 前置条件

- Windows 10 / 11
- Python **3.12**（推荐）：<https://www.python.org/downloads/windows/>
  安装时勾选 **Add python.exe to PATH**
- 代码：`git clone` 或直接解压项目压缩包
- 网络能访问 PyPI

## 1. 准备环境

在项目根目录打开 PowerShell：

```powershell
python --version            # 确认是 3.12.x
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
```

> 如果 PowerShell 禁止执行脚本，先运行：
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 2. 打包

```powershell
python tools\build.py
```

首次约 1~3 分钟。成功后会看到：

```
✅ 打包完成
   产物：...\dist\TermFinale\TermFinale.exe
```

产物是**文件夹** `dist\TermFinale\`，分发时整个文件夹压缩成 zip，不要只发 exe。

## 3. 验收清单

在一台**没装 Python** 的 Windows 上（或虚拟机）逐项确认：

- [ ] 双击 `TermFinale.exe` 能打开，出现欢迎页
- [ ] 右上角「⚙ 设置」能打开，填入 Key 后「测试连接」显示 ✅
- [ ] 新建科目 → 上传 10 页左右 PDF → 能生成讲义
- [ ] 生成的 HTML 能双击用浏览器打开，图片/公式正常
- [ ] 关闭后重开，名字与 Key 仍在
- [ ] 找不到错误时，检查 `%APPDATA%\TermFinale\logs\`

## 4. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 双击闪退，没有任何窗口 | 看 `%APPDATA%\TermFinale\logs\crash.log`；多半是缺 DLL 或杀毒软件拦截 |
| SmartScreen 提示"未知发布者" | 点「更多信息」→「仍要运行」；正式分发可购买代码签名证书 |
| 打包时报 `PermissionError` | 关闭正在运行的 TermFinale，或删掉 `build/`、`dist/` 重试 |
| 打包后体积很大 | 检查是否误把 `onnxruntime`、`numpy` 打进去；`TermFinale.spec` 已排除 |
| 字体显示难看 | 代码已按平台回退到「Microsoft YaHei UI」；如仍异常，截图反馈 |
| 中文路径报错 | 目前路径处理用 pathlib，理论上支持；若报错请记录完整路径 |

## 5. 备注

- 不要在 macOS 上尝试构建 Windows 版；反过来也一样。
- 构建不需要 API Key（Key 是运行时由用户填写的）。
- 如果以后想自动化，可在 GitHub Actions 用 `windows-latest` + 同一份 `TermFinale.spec` 出包。
