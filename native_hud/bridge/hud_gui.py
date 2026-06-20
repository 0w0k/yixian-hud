# -*- coding: utf-8 -*-
"""Settings window + system-tray for the native HUD.

run_gui(settings, on_exit, status_get): a small always-on-top tkinter panel with
show/hide checkboxes (bound live to `settings`), a solo/matchup radio, a status
line, and an Exit button. Closing the window minimizes to the tray (pystray) if
available; the tray menu can re-show or quit. Exit calls on_exit() (which stops
the HUD and closes the spawned game)."""
import threading
import tkinter as tk
from tkinter import ttk

try:                                   # 版本号(发布版由 build_hud 从 tag 注入)
    from hud_version import HUD_VERSION
except Exception:
    HUD_VERSION = "?"
try:                                   # 更新检测(多源轮询);缺失则"关于"里降级显示
    import update_check
except Exception:
    update_check = None

ELEMENTS = [
    ("remaining", "记牌器 剩X"),
    ("damage", "造伤 T1–T8"),
    ("opponent", "对手 命/修"),
    ("warning", "危险牌警告"),
    ("skip", "跳过战斗按钮"),
]

HELP_TEXT = """YiXianHUD 使用说明

【游戏内显示】
· 每张卡右上「剩X」= 该牌在牌库的剩余张数
· 顶部 T1–T8 = 八回合造伤预估
· 左上「敌 命/修」= 对手生命/修为预估
· 红字闪烁 = 对手有危险牌

【快捷键】(可在下方「快捷键」分区自定义)
· Tab = 打开 / 关闭卡池浏览
· D = 鼠标悬浮某张手牌时按 D 换掉它
· 战斗时右上「跳过战斗」按钮 = 跳过动画直接回摆牌

【卡池浏览 (按 Tab)】
· 显示本宗门当前阶段的全部常规牌 + 各牌剩余数
· 右侧「手牌 / 已空 / 危险」切换哪类置顶,其余按剩少在前
· 鼠标滚轮上下滚动,再按 Tab 关闭

【设置面板】
· 显示元素:勾选开关各项显示
· 伤害模式:对打对手(matchup) / 自身输出(solo)
· 位置:填 X,Y 调各文字 / 跳过按钮的位置
· 快捷键:点「改键」后按目标键(支持 Ctrl 组合、鼠标侧键)

提示:本程序仅供个人学习研究,注入有风险、使用可能被封号,详见 EULA。
"""


def _show_help(parent=None):
    """弹出使用说明窗口(设置面板按钮 / 托盘菜单都用它)。"""
    from tkinter import scrolledtext
    win = tk.Toplevel(parent) if parent is not None else tk.Tk()
    win.title("YiXianHUD 使用说明")
    win.geometry("470x560")
    win.attributes("-topmost", True)
    txt = scrolledtext.ScrolledText(win, wrap="word", font=("", 10))
    txt.pack(fill="both", expand=True, padx=10, pady=(10, 6))
    txt.insert("1.0", HELP_TEXT)
    txt.config(state="disabled")
    ttk.Button(win, text="知道了", command=win.destroy).pack(pady=(0, 10))


def _open_releases():
    """打开发布页(给"关于"里的【去下载】用)。"""
    import webbrowser
    url = update_check.RELEASES_URL if update_check else \
        "https://github.com/Airexplosion/yixian-hud/releases"
    try:
        webbrowser.open(url)
    except Exception:
        pass


# 关于窗的署名(作者 + 鸣谢)。yisim=sharp(sharpobject/yisim),
# yixiancardcounter=hiddensquid(gitee hiddensquid12321/yixian-card-counter-with-proxy)。
ABOUT_CREDITS = [
    ("作者", ["Airexplosion", "Kevin"]),
    ("鸣谢", ["sharp —— yisim(伤害模拟引擎)",
              "hiddensquid —— yixiancardcounter(记牌器)"]),
]


def _show_about(parent=None, cached=None):
    """关于窗:当前版本 / 最新版本(后台检测)+ 去下载 + 作者鸣谢。
    cached:启动时已检测的结果(dict),有就直接用,免再请求一次网络。"""
    win = tk.Toplevel(parent) if parent is not None else tk.Tk()
    win.title("关于 YiXianHUD")
    win.geometry("430x430")
    win.attributes("-topmost", True)
    frm = ttk.Frame(win, padding=16)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="YiXianHUD 弈仙牌悬浮助手", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frm, text="当前版本:v%s" % HUD_VERSION).pack(anchor="w", pady=(8, 0))
    latest = ttk.Label(frm, text="最新版本:检测中…", foreground="gray")
    latest.pack(anchor="w")
    ttk.Button(frm, text="去下载最新版", command=_open_releases).pack(anchor="w", pady=(6, 0))

    for title, lines in ABOUT_CREDITS:
        ttk.Separator(frm).pack(fill="x", pady=8)
        ttk.Label(frm, text=title, font=("", 10, "bold")).pack(anchor="w")
        ttk.Label(frm, text="\n".join("· " + s for s in lines),
                  justify="left").pack(anchor="w")

    ttk.Button(frm, text="知道了", command=win.destroy).pack(side="bottom", pady=(10, 0))

    def _render(res):
        if not res or not res.get("ok"):
            latest.config(text="最新版本:检测失败(网络不通,可手动打开下载页)", foreground="#aa6600")
        elif res.get("has_update"):
            latest.config(text="最新版本:v%s  🔴 有新版本可更新!" % res["latest"], foreground="#cc2222")
        else:
            latest.config(text="最新版本:v%s(已是最新 ✓)" % res["latest"], foreground="#22aa66")

    if cached and cached.get("latest") is not None:
        _render(cached)
    elif update_check is not None:
        def _bg():
            res = update_check.check_update(HUD_VERSION)
            try:
                win.after(0, lambda: _render(res))
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()
    else:
        latest.config(text="最新版本:(更新检测模块不可用)", foreground="gray")


def _make_tray(on_show, on_quit, on_help=None, on_about=None):
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return None
    img = Image.new("RGB", (64, 64), (18, 26, 44))
    d = ImageDraw.Draw(img)
    d.ellipse((12, 12, 52, 52), fill=(120, 200, 255))
    items = [pystray.MenuItem("显示设置", lambda icon, item: on_show())]
    if on_help is not None:
        items.append(pystray.MenuItem("使用说明", lambda icon, item: on_help()))
    if on_about is not None:
        items.append(pystray.MenuItem("关于", lambda icon, item: on_about()))
    items.append(pystray.MenuItem("退出", lambda icon, item: on_quit()))
    return pystray.Icon("YiXianHUD", img, "弈仙牌 HUD", pystray.Menu(*items))


def run_gui(settings, on_exit, status_get=None, pos_get=None, on_pos=None,
            hotkey_label=None, hotkey_capture=None):
    root = tk.Tk()
    root.title("弈仙牌 HUD")
    root.geometry("280x600")
    root.attributes("-topmost", True)
    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="显示元素", font=("", 10, "bold")).pack(anchor="w")
    for key, text in ELEMENTS:
        var = tk.BooleanVar(value=bool(settings.get(key, True)))

        def _bind(k=key, v=var):
            settings[k] = bool(v.get())
        ttk.Checkbutton(frm, text=text, variable=var, command=_bind).pack(anchor="w")

    ttk.Separator(frm).pack(fill="x", pady=8)
    ttk.Label(frm, text="伤害模式", font=("", 10, "bold")).pack(anchor="w")
    mode = tk.StringVar(value="matchup" if settings.get("matchup", True) else "solo")

    def _mode():
        settings["matchup"] = (mode.get() == "matchup")
    ttk.Radiobutton(frm, text="对打对手 (matchup)", variable=mode,
                    value="matchup", command=_mode).pack(anchor="w")
    ttk.Radiobutton(frm, text="自身输出 (solo)", variable=mode,
                    value="solo", command=_mode).pack(anchor="w")

    POS_ELEMENTS = [("total", "造伤 T1–T8"), ("warn", "危险牌警告"),
                    ("opp", "对手 命/修"), ("skip", "跳过战斗按钮")]
    ttk.Separator(frm).pack(fill="x", pady=8)
    ttk.Label(frm, text="位置 (X, Y)", font=("", 10, "bold")).pack(anchor="w")
    for key, text in POS_ELEMENTS:
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text=text, width=12).pack(side="left")
        cx, cy = (pos_get(key) if pos_get else (0, 0))
        ex = ttk.Entry(row, width=6)
        ex.insert(0, str(int(cx)))
        ex.pack(side="left")
        ey = ttk.Entry(row, width=6)
        ey.insert(0, str(int(cy)))
        ey.pack(side="left", padx=(4, 0))

        def _push(k=key, exx=ex, eyy=ey):
            try:
                x, y = int(exx.get().strip()), int(eyy.get().strip())
            except ValueError:
                return
            if on_pos:
                on_pos(k, x, y)
        ttk.Button(row, text="应用", width=5, command=_push).pack(side="left", padx=4)

    if hotkey_label and hotkey_capture:
        ttk.Separator(frm).pack(fill="x", pady=8)
        ttk.Label(frm, text="快捷键 (支持 Ctrl组合 / 鼠标侧键)", font=("", 10, "bold")).pack(anchor="w")
        for hk, htext in (("swap", "D牌 换牌"), ("pool", "卡池 浏览")):
            hrow = ttk.Frame(frm)
            hrow.pack(fill="x", pady=1)
            ttk.Label(hrow, text=htext, width=10).pack(side="left")
            hcur = ttk.Label(hrow, text=hotkey_label(hk), width=11, foreground="#22aa66")
            hcur.pack(side="left")

            def _rebind(k=hk, lbl=hcur):
                lbl.config(text="按键中…", foreground="#aa6600")

                def _done():
                    try:
                        lbl.config(text=hotkey_label(k), foreground="#22aa66")
                    except Exception:
                        pass
                hotkey_capture(k, lambda: root.after(0, _done))
            ttk.Button(hrow, text="改键", width=5, command=_rebind).pack(side="left", padx=4)

    ttk.Separator(frm).pack(fill="x", pady=8)
    status = ttk.Label(frm, text="启动中…", foreground="gray", wraplength=230)
    status.pack(anchor="w")
    # 被动更新提示:启动后台检测,有新版才显红字(不弹窗打断);详情在【关于】。
    update_hint = ttk.Label(frm, text="", foreground="#cc2222", wraplength=230)
    update_hint.pack(anchor="w")
    chk = {}                              # 启动检测结果(供【关于】复用,免再请求)

    tray = {"icon": None}

    def _quit():
        if tray["icon"] is not None:
            try:
                tray["icon"].stop()
            except Exception:
                pass
        try:
            on_exit()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

    ttk.Button(frm, text="退出 (关HUD+游戏)", command=_quit).pack(side="bottom", fill="x", pady=(8, 0))
    # 帮助/关于按钮(pack 在退出之后 → 显示在退出上方;关于在最上)
    ttk.Button(frm, text="❓ 使用说明", command=lambda: _show_help(root)).pack(side="bottom", fill="x", pady=(8, 0))
    ttk.Button(frm, text="ℹ️ 关于 / 检查更新",
               command=lambda: _show_about(root, chk)).pack(side="bottom", fill="x", pady=(8, 0))

    # Close button → minimize to tray (don't quit) if a tray icon exists.
    def _on_close():
        if tray["icon"] is not None:
            root.withdraw()
        else:
            _quit()
    root.protocol("WM_DELETE_WINDOW", _on_close)

    icon = _make_tray(on_show=lambda: root.after(0, root.deiconify),
                      on_quit=lambda: root.after(0, _quit),
                      on_help=lambda: root.after(0, lambda: _show_help(root)),
                      on_about=lambda: root.after(0, lambda: _show_about(root, chk)))
    if icon is not None:
        tray["icon"] = icon
        threading.Thread(target=icon.run, daemon=True).start()

    # 启动后台检测最新版(多源轮询);有新版则设置窗顶显红字提示。失败静默。
    if update_check is not None:
        def _startup_check():
            res = update_check.check_update(HUD_VERSION)
            chk.clear()
            chk.update(res)
            if res.get("has_update"):
                def _show():
                    update_hint.config(
                        text="🔴 发现新版本 v%s — 点【关于 / 检查更新】下载" % res["latest"])
                try:
                    root.after(0, _show)
                except Exception:
                    pass
        threading.Thread(target=_startup_check, daemon=True).start()

    if status_get:
        def _tick():
            try:
                status.config(text=status_get())
            except Exception:
                pass
            root.after(1000, _tick)
        _tick()

    root.mainloop()
