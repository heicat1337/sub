#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web 管理面板：编辑配置、运行合并脚本、管理 subconverter
默认监听 http://localhost:8080
"""

import json
import os
import re
import sys
import subprocess
import threading
import time
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, render_template_string, abort

BASE_DIR = Path(__file__).parent.resolve()
SUBCONVERTER_DIR = BASE_DIR / "subconverter"
SUBCONVERTER_EXE = SUBCONVERTER_DIR / ("subconverter.exe" if os.name == "nt" else "subconverter")

EDITABLE_FILES = {
    "subscriptions": {"path": BASE_DIR / "subscriptions.txt", "label": "订阅链接", "lang": "text"},
    "casefarm":      {"path": BASE_DIR / "casefarm.yaml",     "label": "本地代理",     "lang": "yaml"},
    "pref":          {"path": BASE_DIR / "pref.ini",          "label": "转换配置",     "lang": "ini"},
    "group":         {"path": BASE_DIR / "group.txt",         "label": "代理组",       "lang": "text"},
    "rulelist":      {"path": BASE_DIR / "RuleList.txt",      "label": "规则列表",     "lang": "text"},
}

READONLY_FILES = {
    "merged": {"path": BASE_DIR / "merged_config.yaml", "label": "合并后配置", "lang": "yaml"},
    "loon":   {"path": BASE_DIR / "loon_config.conf",   "label": "Loon 配置",   "lang": "text"},
}

GIST_CONFIG_FILE = BASE_DIR / "gist_config.json"
GIST_TOKEN_FILE = BASE_DIR / ".gist_token"

app = Flask(__name__)


# ---------- 运行状态管理 ----------

_run_state = {
    "running": False,
    "logs": [],
    "returncode": None,
    "started_at": None,
    "finished_at": None,
}
_state_lock = threading.Lock()

_subconverter_proc: subprocess.Popen | None = None
_subconverter_lock = threading.Lock()


def _append_log(line: str) -> None:
    with _state_lock:
        _run_state["logs"].append(line)
        if len(_run_state["logs"]) > 5000:
            _run_state["logs"] = _run_state["logs"][-5000:]


def _run_merge_script() -> None:
    with _state_lock:
        _run_state["running"] = True
        _run_state["logs"] = []
        _run_state["returncode"] = None
        _run_state["started_at"] = time.time()
        _run_state["finished_at"] = None
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [sys.executable, "-u", "merge_proxy_config.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
            env=env,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            _append_log(line.rstrip("\n"))
        proc.wait()
        rc = proc.returncode
    except Exception as e:
        _append_log(f"[ERROR] 运行失败: {e}")
        rc = -1
    finally:
        with _state_lock:
            _run_state["running"] = False
            _run_state["returncode"] = rc
            _run_state["finished_at"] = time.time()


# ---------- 文件校验 ----------

def _validate(lang: str, content: str) -> str | None:
    """返回错误信息，或 None 表示通过"""
    if lang == "yaml":
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            return f"YAML 语法错误: {e}"
    return None


TEST_URL = "http://cp.cloudflare.com/generate_204"
SUBSCRIPTION_REGIONS = [
    ("HK 🇭🇰", "AutoHK 🇭🇰", r".*(香港|HK).*$", "60,,20"),
    ("TW 🇨🇳", "AutoTW 🇨🇳", r".*(台湾|台灣|TW).*$", "60,,20"),
    ("KR 🇰🇷", "AutoKR 🇰🇷", r".*(韩国|KR).*$", "60,,20"),
    ("JP 🇯🇵", "AutoJP 🇯🇵", r".*(日本|JP).*$", "60,,20"),
    ("SG 🇸🇬", "AutoSG 🇸🇬", r".*(新加坡|SG).*$", "60,,20"),
    ("AU 🇦🇺", "AutoAU 🇦🇺", r".*(澳大利亚|新西兰|悉尼|墨尔本|奥克兰|Oceania|AU).*$", "60,,20"),
    ("RU 🇷🇺", "AutoRU 🇷🇺", r".*(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯).*$", "60,,30"),
    ("EU 🇪🇺", "AutoEU 🇪🇺", r"^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|乌克兰|卢森堡|德国|意大利|摩尔多瓦|爱尔兰|芬兰|英国|荷兰|以色列|南非).*$", "60,,30"),
    ("CA 🇨🇦", "AutoCA 🇨🇦", r".*(多伦多|加拿大|CA).*$", "60,,30"),
    ("NA 🇺🇲", "AutoNA 🇺🇲", r".*(硅谷|西雅图|美国|US).*$", "60,,30"),
]


def _parse_subscription_lines(content: str) -> list[dict]:
    result = []
    group_id = 0
    for line_index, line in enumerate(content.splitlines()):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split(maxsplit=1)
        url = parts[0]
        label = ""
        if len(parts) > 1:
            tail = parts[1].strip()
            if tail.startswith("#"):
                label = tail[1:].strip()
        result.append({
            "line_index": line_index,
            "group_id": group_id,
            "url": url,
            "label": label or f"订阅{group_id}",
        })
        group_id += 1
    return result


def _insert_group_ref(parts: list[str], ref: str) -> list[str]:
    if ref in parts:
        return parts
    insert_at = len(parts)
    for idx, part in enumerate(parts[2:], start=2):
        if part.startswith("http://") or part.startswith("https://"):
            insert_at = idx
            break
    return parts[:insert_at] + [ref] + parts[insert_at:]


def _remove_group_refs(parts: list[str], refs: set[str]) -> list[str]:
    return [part for part in parts if part not in refs]


def _add_subscription_proxy_groups(group_content: str, label: str, group_id: int) -> str:
    existing_names = {
        line.split("`", 1)[0]
        for line in group_content.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";"))
    }
    group_names = [label] + [f"{label}{suffix}" for suffix, _, _, _ in SUBSCRIPTION_REGIONS]
    if any(name in existing_names for name in group_names):
        raise ValueError(f"group.txt 已存在 {label} 相关代理组")

    lines = []
    for line in group_content.splitlines():
        parts = line.split("`")
        if parts and len(parts) > 1:
            for suffix, auto_name, _, _ in SUBSCRIPTION_REGIONS:
                if parts[0] == auto_name:
                    parts = _insert_group_ref(parts, f"[]{label}{suffix}")
                    break
            line = "`".join(parts)
        lines.append(line)

    block = [f"{label}`select`!!GROUPID={group_id}!!.*"]
    for suffix, _, pattern, params in SUBSCRIPTION_REGIONS:
        block.append(f"{label}{suffix}`url-test`!!GROUPID={group_id}!!{pattern}`[]REJECT`{TEST_URL}`{params}")
    return "\n".join(lines).rstrip() + "\n" + "\n".join(block) + "\n"


def _delete_subscription_proxy_groups(group_content: str, label: str, group_id: int) -> str:
    names = {label} | {f"{label}{suffix}" for suffix, _, _, _ in SUBSCRIPTION_REGIONS}
    refs = {f"[]{name}" for name in names}
    kept_lines = []
    for line in group_content.splitlines():
        parts = line.split("`")
        name = parts[0] if parts else ""
        if name in names:
            continue
        if len(parts) > 1:
            parts = _remove_group_refs(parts, refs)
            line = "`".join(parts)
        kept_lines.append(line)

    def shift_group_id(match):
        current = int(match.group(1))
        if current > group_id:
            current -= 1
        return f"!!GROUPID={current}!!"

    shifted = [re.sub(r"!!GROUPID=(\d+)!!", shift_group_id, line) for line in kept_lines]
    return "\n".join(shifted).rstrip() + "\n"


# ---------- API ----------

@app.route("/api/files")
def api_files():
    return jsonify({
        "editable": {k: {"label": v["label"], "lang": v["lang"]} for k, v in EDITABLE_FILES.items()},
        "readonly": {k: {"label": v["label"], "lang": v["lang"]} for k, v in READONLY_FILES.items()},
    })


@app.route("/api/file/<key>", methods=["GET", "PUT"])
def api_file(key: str):
    entry = EDITABLE_FILES.get(key) or READONLY_FILES.get(key)
    if not entry:
        abort(404)
    path: Path = entry["path"]

    if request.method == "GET":
        try:
            content = path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify({
            "content": content,
            "exists": path.exists(),
            "mtime": path.stat().st_mtime if path.exists() else None,
            "lang": entry["lang"],
            "label": entry["label"],
            "readonly": key in READONLY_FILES,
        })

    if key in READONLY_FILES:
        return jsonify({"error": "只读文件"}), 403

    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    err = _validate(entry["lang"], content)
    if err:
        return jsonify({"error": err}), 400
    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "mtime": path.stat().st_mtime})


@app.route("/api/subscriptions", methods=["POST"])
def api_subscription_add():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    label = (data.get("label") or "").strip()
    if not url:
        return jsonify({"error": "请填写订阅链接"}), 400
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"error": "订阅链接需要以 http:// 或 https:// 开头"}), 400
    if not label:
        return jsonify({"error": "请填写订阅标签，用于生成代理组名称"}), 400
    if any(ch in label for ch in "`\r\n"):
        return jsonify({"error": "订阅标签不能包含反引号或换行"}), 400

    try:
        subs_path = EDITABLE_FILES["subscriptions"]["path"]
        group_path = EDITABLE_FILES["group"]["path"]
        subs_content = subs_path.read_text(encoding="utf-8") if subs_path.exists() else ""
        group_content = group_path.read_text(encoding="utf-8") if group_path.exists() else ""
        subscriptions = _parse_subscription_lines(subs_content)
        if any(item["url"] == url or item["label"] == label for item in subscriptions):
            return jsonify({"error": "订阅链接或标签已存在"}), 400

        group_id = len(subscriptions)
        new_subs = subs_content.rstrip() + ("\n" if subs_content.strip() else "") + f"{url} #{label}\n"
        new_group = _add_subscription_proxy_groups(group_content, label, group_id)

        subs_path.write_text(new_subs, encoding="utf-8", newline="\n")
        group_path.write_text(new_group, encoding="utf-8", newline="\n")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "ok": True,
        "group_id": group_id,
        "subscriptions_content": new_subs,
        "group_content": new_group,
    })


@app.route("/api/subscriptions/<int:group_id>", methods=["DELETE"])
def api_subscription_delete(group_id: int):
    try:
        subs_path = EDITABLE_FILES["subscriptions"]["path"]
        group_path = EDITABLE_FILES["group"]["path"]
        subs_content = subs_path.read_text(encoding="utf-8") if subs_path.exists() else ""
        group_content = group_path.read_text(encoding="utf-8") if group_path.exists() else ""
        subscriptions = _parse_subscription_lines(subs_content)
        target = next((item for item in subscriptions if item["group_id"] == group_id), None)
        if not target:
            return jsonify({"error": "订阅组不存在"}), 404

        lines = subs_content.splitlines()
        del lines[target["line_index"]]
        new_subs = "\n".join(lines).rstrip() + "\n"
        new_group = _delete_subscription_proxy_groups(group_content, target["label"], group_id)

        subs_path.write_text(new_subs, encoding="utf-8", newline="\n")
        group_path.write_text(new_group, encoding="utf-8", newline="\n")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "ok": True,
        "deleted": target,
        "subscriptions_content": new_subs,
        "group_content": new_group,
    })


@app.route("/api/run", methods=["POST"])
def api_run():
    with _state_lock:
        if _run_state["running"]:
            return jsonify({"error": "已有任务正在运行"}), 409
    threading.Thread(target=_run_merge_script, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/run/status")
def api_run_status():
    offset = int(request.args.get("offset", 0))
    with _state_lock:
        logs = _run_state["logs"][offset:]
        return jsonify({
            "running": _run_state["running"],
            "returncode": _run_state["returncode"],
            "started_at": _run_state["started_at"],
            "finished_at": _run_state["finished_at"],
            "logs": logs,
            "total": len(_run_state["logs"]),
        })


@app.route("/api/subconverter/status")
def api_sub_status():
    with _subconverter_lock:
        running = _subconverter_proc is not None and _subconverter_proc.poll() is None
        pid = _subconverter_proc.pid if running else None
    return jsonify({"running": running, "pid": pid, "exists": SUBCONVERTER_EXE.exists()})


@app.route("/api/subconverter/start", methods=["POST"])
def api_sub_start():
    global _subconverter_proc
    with _subconverter_lock:
        if _subconverter_proc and _subconverter_proc.poll() is None:
            return jsonify({"ok": True, "status": "already_running", "pid": _subconverter_proc.pid})
        if not SUBCONVERTER_EXE.exists():
            return jsonify({"error": f"未找到 {SUBCONVERTER_EXE.name}，请先运行 setup_subconverter.bat"}), 400
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            _subconverter_proc = subprocess.Popen(
                [str(SUBCONVERTER_EXE)],
                cwd=str(SUBCONVERTER_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "status": "started", "pid": _subconverter_proc.pid})


@app.route("/api/gist/config")
def api_gist_config():
    cfg = {}
    if GIST_CONFIG_FILE.exists():
        try:
            cfg = json.loads(GIST_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    token_source = None
    if os.getenv("GITHUB_TOKEN"):
        token_source = "env"
    elif GIST_TOKEN_FILE.exists() and GIST_TOKEN_FILE.read_text(encoding="utf-8").strip():
        token_source = "file"
    return jsonify({"gists": cfg, "token_source": token_source})


@app.route("/api/gist/token", methods=["PUT"])
def api_gist_token():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if not token:
        if GIST_TOKEN_FILE.exists():
            GIST_TOKEN_FILE.unlink()
        return jsonify({"ok": True, "cleared": True})
    GIST_TOKEN_FILE.write_text(token, encoding="utf-8")
    try:
        if os.name != "nt":
            os.chmod(GIST_TOKEN_FILE, 0o600)
    except Exception:
        pass
    return jsonify({"ok": True})


@app.route("/api/gist/upload", methods=["POST"])
def api_gist_upload():
    try:
        import importlib
        import upload_to_gist as mod
        importlib.reload(mod)
        result = mod.upload_all()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not result:
        return jsonify({"error": "上传失败，请检查 token 和文件"}), 400
    return jsonify({"ok": True, "gists": result})


@app.route("/api/subconverter/stop", methods=["POST"])
def api_sub_stop():
    global _subconverter_proc
    with _subconverter_lock:
        if not _subconverter_proc or _subconverter_proc.poll() is not None:
            return jsonify({"ok": True, "status": "not_running"})
        try:
            _subconverter_proc.terminate()
            try:
                _subconverter_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _subconverter_proc.kill()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        _subconverter_proc = None
    return jsonify({"ok": True, "status": "stopped"})


# ---------- 页面 ----------

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Proxy 配置面板</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root {
  --bg: #1e1e1e;
  --panel: #252526;
  --panel-2: #2d2d30;
  --border: #3e3e42;
  --text: #d4d4d4;
  --muted: #888;
  --accent: #0e639c;
  --accent-hover: #1177bb;
  --ok: #4ec9b0;
  --err: #f48771;
  --warn: #dcdcaa;
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: var(--bg); color: var(--text); font-size: 13px;
  height: 100vh; display: flex; flex-direction: column;
}
header {
  padding: 10px 16px; background: var(--panel-2); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 16px; flex-shrink: 0;
}
header h1 { margin: 0; font-size: 15px; font-weight: 600; }
header .grow { flex: 1; }
header .status { font-size: 12px; color: var(--muted); }
header .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--muted); margin-right: 6px; vertical-align: middle; }
header .dot.on { background: var(--ok); }
main { flex: 1; display: flex; overflow: hidden; }
aside {
  width: 170px; background: var(--panel); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; flex-shrink: 0;
}
aside .section { padding: 8px 10px; font-size: 11px; text-transform: uppercase; color: var(--muted); letter-spacing: 0.5px; }
aside .tab {
  padding: 8px 16px; cursor: pointer; user-select: none; border-left: 3px solid transparent;
  display: flex; justify-content: space-between; align-items: center;
}
aside .tab:hover { background: var(--panel-2); }
aside .tab.active { background: var(--panel-2); border-left-color: var(--accent); }
aside .tab .ro { font-size: 10px; color: var(--muted); }
aside .tab.dirty::after { content: "●"; color: var(--warn); margin-left: 6px; }
.center { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.toolbar {
  padding: 8px 12px; background: var(--panel-2); border-bottom: 1px solid var(--border);
  display: flex; gap: 8px; align-items: center; flex-shrink: 0;
}
.toolbar .file-info { flex: 1; color: var(--muted); font-size: 12px; }
button {
  background: var(--accent); color: #fff; border: none; padding: 6px 14px;
  border-radius: 3px; cursor: pointer; font-size: 12px;
}
button:hover:not(:disabled) { background: var(--accent-hover); }
button:disabled { opacity: 0.5; cursor: not-allowed; }
button.secondary { background: var(--panel); border: 1px solid var(--border); }
button.secondary:hover:not(:disabled) { background: var(--border); }
button.danger { background: #a1260d; }
button.danger:hover:not(:disabled) { background: #c42b13; }
textarea {
  flex: 1; width: 100%; background: var(--bg); color: var(--text);
  border: none; padding: 12px; font-family: "Consolas", "Menlo", "Courier New", monospace;
  font-size: 13px; resize: none; outline: none; line-height: 1.5;
  tab-size: 2;
}
textarea[readonly] { background: var(--panel); }
.proxy-group-panel {
  display: none; padding: 10px 12px; background: var(--panel); border-bottom: 1px solid var(--border);
  grid-template-columns: minmax(240px, 1fr) minmax(280px, 420px); gap: 10px; flex-shrink: 0;
}
.proxy-group-panel.show { display: grid; }
.proxy-group-list {
  min-height: 170px; max-height: 280px; overflow-y: auto; border: 1px solid var(--border);
  background: var(--bg);
}
.proxy-group-row {
  width: 100%; padding: 7px 9px; border-bottom: 1px solid var(--border); display: grid;
  grid-template-columns: minmax(100px, 1fr) 80px 52px; gap: 8px; align-items: center;
  color: var(--text); background: transparent; cursor: pointer; text-align: left; border-radius: 0;
}
.proxy-group-row:hover { background: var(--panel-2); }
.proxy-group-row.active { background: #094771; }
.proxy-group-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.proxy-group-row .meta { color: var(--muted); font-size: 11px; }
.proxy-group-empty { padding: 24px 12px; color: var(--muted); text-align: center; }
.proxy-group-form {
  display: grid; grid-template-columns: 1fr 92px; gap: 8px; align-content: start;
}
.proxy-group-form label { display: grid; gap: 4px; color: var(--muted); font-size: 11px; }
.proxy-group-form input,
.proxy-group-form select,
.proxy-group-form textarea {
  width: 100%; min-height: 0; background: var(--bg); color: var(--text); border: 1px solid var(--border);
  border-radius: 3px; padding: 6px 8px; font-size: 12px; font-family: inherit;
}
.proxy-group-form textarea { grid-column: 1 / -1; height: 74px; resize: vertical; line-height: 1.4; }
.proxy-group-actions { grid-column: 1 / -1; display: flex; gap: 8px; justify-content: flex-end; }
.subscription-panel {
  display: none; padding: 10px 12px; background: var(--panel); border-bottom: 1px solid var(--border);
  grid-template-columns: minmax(260px, 1fr) minmax(280px, 420px); gap: 10px; flex-shrink: 0;
}
.subscription-panel.show { display: grid; }
.subscription-list {
  min-height: 150px; max-height: 260px; overflow-y: auto; border: 1px solid var(--border);
  background: var(--bg);
}
.subscription-row {
  width: 100%; padding: 7px 9px; border-bottom: 1px solid var(--border); display: grid;
  grid-template-columns: 42px minmax(84px, 130px) minmax(120px, 1fr); gap: 8px; align-items: center;
  color: var(--text); background: transparent; cursor: pointer; text-align: left; border-radius: 0;
}
.subscription-row:hover { background: var(--panel-2); }
.subscription-row.active { background: #094771; }
.subscription-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.subscription-row .meta { color: var(--muted); font-size: 11px; }
.subscription-empty { padding: 24px 12px; color: var(--muted); text-align: center; }
.subscription-form {
  display: grid; grid-template-columns: 1fr 112px; gap: 8px; align-content: start;
}
.subscription-form label { display: grid; gap: 4px; color: var(--muted); font-size: 11px; }
.subscription-form input {
  width: 100%; background: var(--bg); color: var(--text); border: 1px solid var(--border);
  border-radius: 3px; padding: 6px 8px; font-size: 12px; font-family: inherit;
}
.subscription-form .wide { grid-column: 1 / -1; }
.subscription-actions { grid-column: 1 / -1; display: flex; gap: 8px; justify-content: flex-end; }
.right {
  width: 380px; background: var(--panel); border-left: 1px solid var(--border);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.right .block { padding: 12px; border-bottom: 1px solid var(--border); }
.right h2 { margin: 0 0 10px 0; font-size: 12px; text-transform: uppercase; color: var(--muted); letter-spacing: 0.5px; }
.right .row { display: flex; gap: 6px; margin-top: 6px; }
.logs {
  flex: 1; overflow-y: auto; padding: 8px 12px; font-family: "Consolas", "Menlo", monospace;
  font-size: 12px; background: var(--bg); white-space: pre-wrap; line-height: 1.4;
}
.logs .err { color: var(--err); }
.logs .ok { color: var(--ok); }
.logs .warn { color: var(--warn); }
.toast {
  position: fixed; bottom: 20px; right: 20px; padding: 10px 16px;
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 4px;
  opacity: 0; transition: opacity 0.2s; max-width: 400px;
}
.toast.show { opacity: 1; }
.toast.err { border-color: var(--err); color: var(--err); }
.toast.ok { border-color: var(--ok); color: var(--ok); }
</style>
</head>
<body>
<header>
  <h1>⚡ Proxy 配置面板</h1>
  <div class="grow"></div>
  <div class="status">
    <span class="dot" id="sub-dot"></span><span id="sub-status">Subconverter: —</span>
  </div>
</header>
<main>
  <aside>
    <div class="section">可编辑</div>
    <div id="tabs-editable"></div>
    <div class="section">输出</div>
    <div id="tabs-readonly"></div>
  </aside>
  <div class="center">
    <div class="toolbar">
      <div class="file-info" id="file-info">—</div>
      <button class="secondary" id="btn-reload">重新加载</button>
      <button id="btn-save">保存</button>
    </div>
    <div class="subscription-panel" id="subscription-panel">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <strong>订阅组</strong>
          <button class="secondary" id="btn-subscription-refresh" style="padding:4px 8px;">从文本刷新</button>
        </div>
        <div class="subscription-list" id="subscription-list"></div>
        <div style="margin-top:6px; color:var(--muted); font-size:11px;">序号对应 group.txt 中的 GROUPID，调整订阅顺序后要同步检查代理组。</div>
      </div>
      <div class="subscription-form">
        <label class="wide">订阅链接
          <input id="subscription-url" placeholder="https://example.com/sub">
        </label>
        <label>标签
          <input id="subscription-label" placeholder="例如 雨燕云">
        </label>
        <label>GROUPID
          <input id="subscription-next-id" readonly>
        </label>
        <div class="subscription-actions">
          <button class="danger" id="btn-subscription-delete" disabled>删除选中</button>
          <button id="btn-subscription-add">新增订阅组</button>
        </div>
      </div>
    </div>
    <div class="proxy-group-panel" id="proxy-group-panel">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <strong>代理组</strong>
          <button class="secondary" id="btn-group-refresh" style="padding:4px 8px;">从文本刷新</button>
        </div>
        <div class="proxy-group-list" id="proxy-group-list"></div>
      </div>
      <div class="proxy-group-form">
        <label>组名
          <input id="group-name" placeholder="例如 Netflix">
        </label>
        <label>类型
          <select id="group-type">
            <option value="select">select</option>
            <option value="url-test">url-test</option>
            <option value="fallback">fallback</option>
            <option value="load-balance">load-balance</option>
          </select>
        </label>
        <label style="grid-column:1 / -1;">节点/策略/规则（一行一个，DIRECT/REJECT 会自动加 []）
          <textarea id="group-items" placeholder="B1gProxy&#10;AutoHK 🇭🇰&#10;DIRECT"></textarea>
        </label>
        <label>测试 URL
          <input id="group-url" value="http://cp.cloudflare.com/generate_204">
        </label>
        <label>间隔/容差
          <input id="group-params" value="60,,20">
        </label>
        <div class="proxy-group-actions">
          <button class="danger" id="btn-group-delete" disabled>删除选中</button>
          <button id="btn-group-add">新增代理组</button>
        </div>
      </div>
    </div>
    <textarea id="editor" spellcheck="false" placeholder="加载中..."></textarea>
  </div>
  <div class="right">
    <div class="block">
      <h2>Subconverter 服务</h2>
      <div class="row">
        <button class="secondary" id="btn-sub-start">启动</button>
        <button class="secondary" id="btn-sub-stop">停止</button>
      </div>
    </div>
    <div class="block">
      <h2>合并脚本</h2>
      <div class="row">
        <button id="btn-run">运行 merge_proxy_config.py</button>
      </div>
    </div>
    <div class="block">
      <h2>Gist 上传</h2>
      <div style="margin-bottom: 8px;">
        <div style="font-size: 11px; color: var(--muted); margin-bottom: 4px;">GITHUB_TOKEN <span id="token-source"></span></div>
        <input type="password" id="gist-token" placeholder="ghp_..." autocomplete="off"
               style="width:100%; background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 5px 8px; border-radius: 3px; font-family: monospace; font-size: 12px;">
      </div>
      <div class="row">
        <button class="secondary" id="btn-save-token">保存 Token</button>
        <button id="btn-gist-upload">立即上传</button>
      </div>
      <div id="gist-urls" style="margin-top: 10px; font-size: 11px; font-family: monospace; word-break: break-all;"></div>
    </div>
    <div class="block" style="flex:1; display:flex; flex-direction:column; padding: 0;">
      <div style="padding: 12px 12px 6px 12px;">
        <h2 style="display:inline-block;">运行日志</h2>
        <button class="secondary" style="float:right; padding: 3px 8px; font-size: 11px;" id="btn-clear-logs">清空</button>
      </div>
      <div class="logs" id="logs"></div>
    </div>
  </div>
</main>
<div class="toast" id="toast"></div>

<script>
const state = {
  currentKey: null,
  files: {},
  dirty: new Set(),
  selectedGroupIndex: null,
  selectedSubscriptionIndex: null,
  logOffset: 0,
  runPolling: false,
};

function toast(msg, type) {
  const el = document.getElementById('toast');
  el.className = 'toast show ' + (type || '');
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.className = 'toast', 2500);
}

async function api(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function currentIsProxyGroup() {
  return state.currentKey === 'group';
}

function currentIsSubscriptions() {
  return state.currentKey === 'subscriptions';
}

function markDirty(key) {
  if (!key) return;
  state.dirty.add(key);
  renderTabs();
}

function parseProxyGroups(content) {
  return content.split(/\r?\n/).map((line, index) => {
    const raw = line.trim();
    if (!raw || raw.startsWith(';') || raw.startsWith('#')) return null;
    const parts = raw.split('`');
    if (parts.length < 2) return null;
    return {
      index,
      raw: line,
      name: parts[0] || '(未命名)',
      type: parts[1] || '',
      items: Math.max(parts.length - 2, 0),
    };
  }).filter(Boolean);
}

function parseSubscriptions(content) {
  let groupId = 0;
  return content.split(/\r?\n/).map((line, index) => {
    const raw = line.trim();
    if (!raw || raw.startsWith('#')) return null;
    const match = raw.match(/^(\S+)(?:\s+#\s*(.*))?$/);
    if (!match) return null;
    const item = {
      index,
      groupId,
      raw: line,
      url: match[1],
      label: (match[2] || '').trim() || `订阅${groupId}`,
    };
    groupId += 1;
    return item;
  }).filter(Boolean);
}

function renderSubscriptions() {
  const panel = document.getElementById('subscription-panel');
  const list = document.getElementById('subscription-list');
  if (!currentIsSubscriptions()) {
    panel.classList.remove('show');
    state.selectedSubscriptionIndex = null;
    return;
  }
  panel.classList.add('show');
  const subscriptions = parseSubscriptions(document.getElementById('editor').value);
  if (state.selectedSubscriptionIndex != null && !subscriptions.some(sub => sub.index === state.selectedSubscriptionIndex)) {
    state.selectedSubscriptionIndex = null;
  }
  list.innerHTML = '';
  if (!subscriptions.length) {
    const empty = document.createElement('div');
    empty.className = 'subscription-empty';
    empty.textContent = '暂无订阅组';
    list.appendChild(empty);
  }
  for (const sub of subscriptions) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'subscription-row' + (state.selectedSubscriptionIndex === sub.index ? ' active' : '');
    row.dataset.index = String(sub.index);

    const id = document.createElement('span');
    id.className = 'meta';
    id.textContent = `#${sub.groupId}`;
    const label = document.createElement('span');
    label.textContent = sub.label;
    const url = document.createElement('span');
    url.className = 'meta';
    url.textContent = sub.url;

    row.appendChild(id);
    row.appendChild(label);
    row.appendChild(url);
    row.onclick = () => {
      state.selectedSubscriptionIndex = sub.index;
      renderSubscriptions();
    };
    list.appendChild(row);
  }
  document.getElementById('subscription-next-id').value = String(subscriptions.length);
  document.getElementById('btn-subscription-delete').disabled = state.selectedSubscriptionIndex == null;
}

function buildSubscriptionLine() {
  const url = document.getElementById('subscription-url').value.trim();
  const label = document.getElementById('subscription-label').value.trim();
  if (!url) throw new Error('请填写订阅链接');
  if (!/^https?:\/\//i.test(url)) throw new Error('订阅链接需要以 http:// 或 https:// 开头');
  return label ? `${url} #${label}` : url;
}

function appendSubscriptionLine(line) {
  const editor = document.getElementById('editor');
  const content = editor.value.replace(/\s+$/g, '');
  editor.value = content ? `${content}\n${line}\n` : `${line}\n`;
  state.selectedSubscriptionIndex = editor.value.split(/\r?\n/).length - 2;
  markDirty('subscriptions');
  renderSubscriptions();
}

function deleteSelectedSubscription() {
  if (state.selectedSubscriptionIndex == null) return;
  const editor = document.getElementById('editor');
  const target = parseSubscriptions(editor.value).find(sub => sub.index === state.selectedSubscriptionIndex);
  if (!target) return;
  const label = target.label;
  if (!confirm(`确定删除订阅组「${label}」？删除后后续 GROUPID 会前移。`)) return;
  return target;
}

function renderProxyGroups() {
  const panel = document.getElementById('proxy-group-panel');
  const list = document.getElementById('proxy-group-list');
  if (!currentIsProxyGroup()) {
    panel.classList.remove('show');
    state.selectedGroupIndex = null;
    return;
  }
  panel.classList.add('show');
  const groups = parseProxyGroups(document.getElementById('editor').value);
  if (state.selectedGroupIndex != null && !groups.some(group => group.index === state.selectedGroupIndex)) {
    state.selectedGroupIndex = null;
  }
  list.innerHTML = '';
  if (!groups.length) {
    const empty = document.createElement('div');
    empty.className = 'proxy-group-empty';
    empty.textContent = '暂无可识别的代理组';
    list.appendChild(empty);
  }
  for (const group of groups) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'proxy-group-row' + (state.selectedGroupIndex === group.index ? ' active' : '');
    row.dataset.index = String(group.index);

    const name = document.createElement('span');
    name.textContent = group.name;
    const type = document.createElement('span');
    type.className = 'meta';
    type.textContent = group.type;
    const count = document.createElement('span');
    count.className = 'meta';
    count.textContent = `${group.items}项`;

    row.appendChild(name);
    row.appendChild(type);
    row.appendChild(count);
    row.onclick = () => {
      state.selectedGroupIndex = group.index;
      renderProxyGroups();
    };
    list.appendChild(row);
  }
  document.getElementById('btn-group-delete').disabled = state.selectedGroupIndex == null;
}

function normalizeGroupItem(item) {
  const value = item.trim();
  if (!value) return '';
  if (value.startsWith('[]') || value.startsWith('!!') || /^https?:\/\//i.test(value) || /^\d/.test(value)) {
    return value;
  }
  return `[]${value}`;
}

function buildProxyGroupLine() {
  const name = document.getElementById('group-name').value.trim();
  const type = document.getElementById('group-type').value;
  const rawItems = document.getElementById('group-items').value
    .split(/[\n,`]+/)
    .map(normalizeGroupItem)
    .filter(Boolean);
  if (!name) throw new Error('请填写代理组名称');
  if (!rawItems.length) throw new Error('请至少填写一个节点、策略或规则');

  const parts = [name, type, ...rawItems];
  if (type !== 'select') {
    const url = document.getElementById('group-url').value.trim();
    const params = document.getElementById('group-params').value.trim();
    if (url) parts.push(url);
    if (params) parts.push(params);
  }
  return parts.join('`');
}

function appendProxyGroupLine(line) {
  const editor = document.getElementById('editor');
  const content = editor.value.replace(/\s+$/g, '');
  editor.value = content ? `${content}\n${line}\n` : `${line}\n`;
  state.selectedGroupIndex = editor.value.split(/\r?\n/).length - 2;
  markDirty('group');
  renderProxyGroups();
}

function deleteSelectedProxyGroup() {
  if (state.selectedGroupIndex == null) return;
  const editor = document.getElementById('editor');
  const lines = editor.value.split(/\r?\n/);
  const target = lines[state.selectedGroupIndex];
  if (target == null) return;
  const name = target.split('`')[0] || target;
  if (!confirm(`确定删除代理组「${name}」？`)) return;
  lines.splice(state.selectedGroupIndex, 1);
  editor.value = lines.join('\n').replace(/\n*$/g, '\n');
  state.selectedGroupIndex = null;
  markDirty('group');
  renderProxyGroups();
}

function renderTabs() {
  const makeTab = (key, meta, ro) => {
    const div = document.createElement('div');
    div.className = 'tab' + (state.currentKey === key ? ' active' : '') + (state.dirty.has(key) ? ' dirty' : '');
    div.dataset.key = key;
    div.innerHTML = `<span>${meta.label}</span>` + (ro ? `<span class="ro">只读</span>` : `<span class="ro">${meta.lang}</span>`);
    div.onclick = () => selectFile(key);
    return div;
  };
  const ed = document.getElementById('tabs-editable');
  const ro = document.getElementById('tabs-readonly');
  ed.innerHTML = '';
  ro.innerHTML = '';
  for (const [k, v] of Object.entries(state.files.editable)) ed.appendChild(makeTab(k, v, false));
  for (const [k, v] of Object.entries(state.files.readonly)) ro.appendChild(makeTab(k, v, true));
}

async function selectFile(key) {
  if (state.dirty.has(state.currentKey)) {
    if (!confirm('当前文件有未保存的修改，确定切换？')) return;
    state.dirty.delete(state.currentKey);
  }
  state.currentKey = key;
  renderTabs();
  const editor = document.getElementById('editor');
  editor.value = '加载中...';
  editor.readOnly = true;
  try {
    const data = await api(`/api/file/${key}`);
    editor.value = data.content;
    editor.readOnly = data.readonly;
    state.selectedGroupIndex = null;
    state.selectedSubscriptionIndex = null;
    renderSubscriptions();
    renderProxyGroups();
    const info = document.getElementById('file-info');
    const mt = data.mtime ? new Date(data.mtime * 1000).toLocaleString() : '文件不存在';
    info.textContent = `${data.label} · ${data.lang}${data.readonly ? ' · 只读' : ''} · ${mt}`;
    document.getElementById('btn-save').disabled = data.readonly;
  } catch (e) {
    toast('加载失败: ' + e.message, 'err');
  }
}

document.getElementById('editor').addEventListener('input', () => {
  if (state.currentKey) {
    markDirty(state.currentKey);
    if (currentIsSubscriptions()) renderSubscriptions();
    if (currentIsProxyGroup()) renderProxyGroups();
  }
});

async function saveCurrentEditor(silent) {
  if (!state.currentKey) return;
  const content = document.getElementById('editor').value;
  await api(`/api/file/${state.currentKey}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content}),
  });
  state.dirty.delete(state.currentKey);
  renderTabs();
  if (!silent) toast('已保存', 'ok');
}

document.getElementById('btn-subscription-refresh').onclick = () => {
  state.selectedSubscriptionIndex = null;
  renderSubscriptions();
};

document.getElementById('btn-subscription-add').onclick = async () => {
  try {
    if (state.dirty.has('subscriptions')) await saveCurrentEditor(true);
    const url = document.getElementById('subscription-url').value.trim();
    const label = document.getElementById('subscription-label').value.trim();
    const data = await api('/api/subscriptions', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url, label}),
    });
    document.getElementById('editor').value = data.subscriptions_content;
    state.selectedSubscriptionIndex = null;
    state.dirty.delete('subscriptions');
    document.getElementById('subscription-url').value = '';
    document.getElementById('subscription-label').value = '';
    renderTabs();
    renderSubscriptions();
    toast('订阅组和代理组已新增', 'ok');
  } catch (e) {
    toast(e.message, 'err');
  }
};

document.getElementById('btn-subscription-delete').onclick = async () => {
  const target = deleteSelectedSubscription();
  if (!target) return;
  try {
    if (state.dirty.has('subscriptions')) await saveCurrentEditor(true);
    const data = await api(`/api/subscriptions/${target.groupId}`, {method: 'DELETE'});
    document.getElementById('editor').value = data.subscriptions_content;
    state.selectedSubscriptionIndex = null;
    state.dirty.delete('subscriptions');
    renderTabs();
    renderSubscriptions();
    toast('订阅组和对应代理组已删除', 'ok');
  } catch (e) {
    toast(e.message, 'err');
  }
};

document.getElementById('btn-group-refresh').onclick = () => {
  state.selectedGroupIndex = null;
  renderProxyGroups();
};

document.getElementById('btn-group-add').onclick = () => {
  try {
    appendProxyGroupLine(buildProxyGroupLine());
    document.getElementById('group-name').value = '';
    document.getElementById('group-items').value = '';
    toast('代理组已新增，请保存文件', 'ok');
  } catch (e) {
    toast(e.message, 'err');
  }
};

document.getElementById('btn-group-delete').onclick = deleteSelectedProxyGroup;

document.getElementById('btn-save').onclick = async () => {
  if (!state.currentKey) return;
  const content = document.getElementById('editor').value;
  try {
    await api(`/api/file/${state.currentKey}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({content}),
    });
    state.dirty.delete(state.currentKey);
    renderTabs();
    toast('已保存', 'ok');
    // 刷新 mtime
    const data = await api(`/api/file/${state.currentKey}`);
    const info = document.getElementById('file-info');
    const mt = data.mtime ? new Date(data.mtime * 1000).toLocaleString() : '文件不存在';
    info.textContent = `${data.label} · ${data.lang} · ${mt}`;
  } catch (e) {
    toast('保存失败: ' + e.message, 'err');
  }
};

document.getElementById('btn-reload').onclick = () => {
  if (!state.currentKey) return;
  state.dirty.delete(state.currentKey);
  selectFile(state.currentKey);
};

document.getElementById('btn-run').onclick = async () => {
  try {
    await api('/api/run', {method: 'POST'});
    state.logOffset = 0;
    document.getElementById('logs').textContent = '';
    pollRun();
  } catch (e) {
    toast('运行失败: ' + e.message, 'err');
  }
};

document.getElementById('btn-clear-logs').onclick = () => {
  document.getElementById('logs').textContent = '';
  state.logOffset = 0;
};

async function pollRun() {
  if (state.runPolling) return;
  state.runPolling = true;
  const runBtn = document.getElementById('btn-run');
  const logsEl = document.getElementById('logs');
  try {
    while (true) {
      const data = await api(`/api/run/status?offset=${state.logOffset}`);
      if (data.logs && data.logs.length) {
        for (const line of data.logs) {
          const div = document.createElement('div');
          if (/error|失败|错误/i.test(line)) div.className = 'err';
          else if (/warning|警告/i.test(line)) div.className = 'warn';
          else if (/完成|成功|已|saved/i.test(line)) div.className = 'ok';
          div.textContent = line;
          logsEl.appendChild(div);
        }
        state.logOffset = data.total;
        logsEl.scrollTop = logsEl.scrollHeight;
      }
      runBtn.disabled = data.running;
      runBtn.textContent = data.running ? '运行中...' : '运行 merge_proxy_config.py';
      if (!data.running) {
        if (data.returncode === 0) toast('运行完成', 'ok');
        else if (data.returncode != null) toast(`运行失败 (code=${data.returncode})`, 'err');
        break;
      }
      await new Promise(r => setTimeout(r, 600));
    }
  } finally {
    state.runPolling = false;
  }
}

async function refreshSubStatus() {
  try {
    const data = await api('/api/subconverter/status');
    const dot = document.getElementById('sub-dot');
    const text = document.getElementById('sub-status');
    dot.className = 'dot' + (data.running ? ' on' : '');
    text.textContent = 'Subconverter: ' + (data.running ? `运行中 (PID ${data.pid})` : (data.exists ? '已停止' : '未安装'));
  } catch (e) {}
}

document.getElementById('btn-sub-start').onclick = async () => {
  try {
    const d = await api('/api/subconverter/start', {method: 'POST'});
    toast(d.status === 'already_running' ? 'Subconverter 已在运行' : 'Subconverter 已启动', 'ok');
    refreshSubStatus();
  } catch (e) {
    toast(e.message, 'err');
  }
};

document.getElementById('btn-sub-stop').onclick = async () => {
  try {
    await api('/api/subconverter/stop', {method: 'POST'});
    toast('Subconverter 已停止', 'ok');
    refreshSubStatus();
  } catch (e) {
    toast(e.message, 'err');
  }
};

async function refreshGistConfig() {
  try {
    const data = await api('/api/gist/config');
    const src = document.getElementById('token-source');
    if (data.token_source === 'env') src.textContent = '(环境变量已设置)';
    else if (data.token_source === 'file') src.textContent = '(.gist_token 已保存)';
    else src.textContent = '(未设置)';
    const urlsDiv = document.getElementById('gist-urls');
    urlsDiv.innerHTML = '';
    for (const [k, v] of Object.entries(data.gists || {})) {
      const div = document.createElement('div');
      div.style.marginBottom = '4px';
      div.innerHTML = `<span style="color: var(--muted);">${k}:</span> <a href="${v.html_url}" target="_blank" style="color: var(--accent-hover);">${v.html_url}</a>`;
      urlsDiv.appendChild(div);
    }
  } catch (e) {}
}

document.getElementById('btn-save-token').onclick = async () => {
  const token = document.getElementById('gist-token').value.trim();
  try {
    await api('/api/gist/token', {
      method: 'PUT', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token}),
    });
    document.getElementById('gist-token').value = '';
    toast(token ? 'Token 已保存' : 'Token 已清空', 'ok');
    refreshGistConfig();
  } catch (e) { toast(e.message, 'err'); }
};

document.getElementById('btn-gist-upload').onclick = async () => {
  const btn = document.getElementById('btn-gist-upload');
  btn.disabled = true; btn.textContent = '上传中...';
  try {
    await api('/api/gist/upload', {method: 'POST'});
    toast('上传成功', 'ok');
    refreshGistConfig();
  } catch (e) { toast(e.message, 'err'); }
  finally { btn.disabled = false; btn.textContent = '立即上传'; }
};

(async () => {
  state.files = await api('/api/files');
  renderTabs();
  const firstKey = Object.keys(state.files.editable)[0];
  if (firstKey) selectFile(firstKey);
  refreshSubStatus();
  refreshGistConfig();
  setInterval(refreshSubStatus, 5000);
  // 恢复可能在运行中的任务
  const s = await api('/api/run/status');
  if (s.running || s.logs.length) pollRun();
})();

window.addEventListener('beforeunload', (e) => {
  if (state.dirty.size > 0) {
    e.preventDefault();
    e.returnValue = '';
  }
});
</script>
</body>
</html>
"""


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Proxy 配置面板 Web 服务")
    ap.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    ap.add_argument("--port", type=int, default=8080, help="监听端口（默认 8080）")
    ap.add_argument("--debug", action="store_true", help="开启调试模式")
    args = ap.parse_args()

    print(f" * 启动 Web 面板: http://{args.host}:{args.port}")
    print(f" * 工作目录: {BASE_DIR}")
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
