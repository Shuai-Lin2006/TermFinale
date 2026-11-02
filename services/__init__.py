"""服务层：编排生成流水线，不依赖任何 UI 框架。

桌面端（CustomTkinter）与未来的 Web 端都只调用这里；
进度通过 ``on_progress`` 回调上报，取消通过 ``stop_event``。
"""
