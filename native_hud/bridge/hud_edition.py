# -*- coding: utf-8 -*-
"""版本变体标记(由 build_hud.py 按 --lite / --attach 写入)。

LITE=True:精简版,只记牌器 + 跳过战斗,完全不带 yisim/伤害(不起 total_loop、不打包
node、GUI 隐藏伤害项)。ATTACH=True:默认 attach 已运行的游戏(而非 spawn 拉起);
两者都可被环境变量 YX_ATTACH 覆盖。默认 False = 完整版 + spawn。
"""
LITE = False
ATTACH = False
