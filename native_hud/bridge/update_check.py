# -*- coding: utf-8 -*-
"""检测 GitHub 最新发布版,多源轮询(有人连不上 GitHub)。

依次试多个源,首个成功即返回最新版本号:
  1. GitHub API 直连
  2. jsdelivr data API(国内通常可达,返回 gh 仓库的最新 tag)
  3. 若干 ghproxy 系镜像代理 GitHub API

全程用 urllib(stdlib,免依赖 requests),每源短超时;调用方请放后台线程跑,别卡 GUI。
"""
from __future__ import annotations
import json
import re
import urllib.request

REPO = "Airexplosion/yixian-hud"
RELEASES_URL = "https://github.com/%s/releases" % REPO   # 给用户点【去下载】

_UA = {"User-Agent": "YiXianHUD-update-check"}
_TIMEOUT = 6

# ghproxy 系镜像前缀(代理 https://api.github.com/...);失效一个不影响其它源。
_API_MIRRORS = [
    "https://ghproxy.com/",
    "https://mirror.ghproxy.com/",
    "https://ghproxy.net/",
    "https://ghfast.top/",
]


def _norm(tag):
    """'v1.0.6' / '1.0.6' / 'V1.2' → (1,0,6) 元组;取不到数字 → None。"""
    if not tag:
        return None
    m = re.search(r"(\d+(?:\.\d+)+)", str(tag))
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def _get(url, timeout=_TIMEOUT):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _src_api(prefix=""):
    """GitHub releases/latest 的 JSON(prefix 为空=直连,否则走镜像)→ tag_name。"""
    url = "%shttps://api.github.com/repos/%s/releases/latest" % (prefix, REPO)
    return json.loads(_get(url)).get("tag_name")


def _src_jsdelivr():
    """jsdelivr 的 gh 包元数据:{tags:{latest},versions:[...]} → 最新 tag。"""
    j = json.loads(_get("https://data.jsdelivr.com/v1/packages/gh/%s" % REPO))
    return (j.get("tags") or {}).get("latest") or (j.get("versions") or [None])[0]


def _sources():
    """(名字, 取版本函数) 序列;按可达性/可靠性排序。"""
    yield ("github-api", _src_api)
    yield ("jsdelivr", _src_jsdelivr)
    for m in _API_MIRRORS:
        yield ("mirror:" + m, (lambda mm=m: _src_api(mm)))


def latest_version():
    """轮询所有源,返回首个成功的最新版本号字符串(可能带 v);全失败 → None。"""
    for _name, fn in _sources():
        try:
            tag = fn()
            if _norm(tag):
                return str(tag)
        except Exception:
            continue
    return None


def check_update(current):
    """→ {current, latest, has_update, ok}。ok=False = 所有源都失败(离线/全被墙)。"""
    latest = latest_version()
    if latest is None:
        return {"current": current, "latest": None, "has_update": False, "ok": False}
    cv, lv = _norm(current), _norm(latest)
    return {"current": current, "latest": latest,
            "has_update": bool(cv and lv and lv > cv), "ok": True}
