#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将合并后的配置上传到 GitHub Gist。

- 两个文件分别上传到两个独立的 Gist（每个文件一个 ID）
- 首次运行会自动创建 Gist 并将 ID 保存到 gist_config.json
- 后续运行通过 PATCH 更新同一个 Gist
- Token 来源（优先级从高到低）：
    1. 环境变量 GITHUB_TOKEN
    2. 项目根目录下 .gist_token 文件（单行 token）
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests

BASE_DIR = Path(__file__).parent.resolve()
GIST_CONFIG_FILE = BASE_DIR / "gist_config.json"
TOKEN_FILE = BASE_DIR / ".gist_token"
API_BASE = "https://api.github.com"

# 要上传的文件：key 用于 gist_config.json 中索引
UPLOAD_FILES = {
    "loon": {
        "path": BASE_DIR / "loon_config.conf",
        "gist_filename": "loon_config.conf",
        "description": "Loon configuration (auto-generated)",
    },
    "merged": {
        "path": BASE_DIR / "merged_config.yaml",
        "gist_filename": "merged_config.yaml",
        "description": "Merged Clash configuration (auto-generated)",
    },
}


def get_token() -> Optional[str]:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


def load_config() -> dict:
    if GIST_CONFIG_FILE.exists():
        try:
            return json.loads(GIST_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"警告: 读取 {GIST_CONFIG_FILE.name} 失败: {e}")
    return {}


def save_config(cfg: dict) -> None:
    GIST_CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def create_gist(token: str, filename: str, content: str, description: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/gists",
        headers=_headers(token),
        json={
            "description": description,
            "public": False,
            "files": {filename: {"content": content}},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def update_gist(token: str, gist_id: str, filename: str, content: str) -> dict:
    resp = requests.patch(
        f"{API_BASE}/gists/{gist_id}",
        headers=_headers(token),
        json={"files": {filename: {"content": content}}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def upload_file(token: str, key: str, cfg: dict) -> Optional[dict]:
    meta = UPLOAD_FILES[key]
    path: Path = meta["path"]
    if not path.exists():
        print(f"[{key}] 跳过：{path.name} 不存在")
        return None

    content = path.read_text(encoding="utf-8")
    entry = cfg.get(key) or {}
    gist_id = entry.get("id")

    try:
        if gist_id:
            print(f"[{key}] 更新 gist {gist_id}")
            data = update_gist(token, gist_id, meta["gist_filename"], content)
        else:
            print(f"[{key}] 创建新 gist ({meta['gist_filename']})")
            data = create_gist(token, meta["gist_filename"], content, meta["description"])
    except requests.HTTPError as e:
        body = e.response.text if e.response is not None else ""
        # gist 被删或 ID 无效时重新创建一次
        if gist_id and e.response is not None and e.response.status_code in (404, 422):
            print(f"[{key}] gist {gist_id} 无效 ({e.response.status_code})，重建")
            data = create_gist(token, meta["gist_filename"], content, meta["description"])
        else:
            print(f"[{key}] 上传失败: {e} {body}")
            return None
    except Exception as e:
        print(f"[{key}] 上传失败: {e}")
        return None

    owner = data.get("owner", {}).get("login", "")
    gist_id = data["id"]
    stable_raw = f"https://gist.githubusercontent.com/{owner}/{gist_id}/raw/{meta['gist_filename']}"
    file_info = data.get("files", {}).get(meta["gist_filename"], {})
    result = {
        "id": gist_id,
        "html_url": data["html_url"],
        "raw_url": stable_raw,
        "versioned_raw_url": file_info.get("raw_url"),
        "filename": meta["gist_filename"],
        "updated_at": data.get("updated_at"),
    }
    print(f"[{key}] {result['raw_url']}")
    return result


def upload_all() -> dict:
    token = get_token()
    if not token:
        print("错误: 未找到 GITHUB_TOKEN（环境变量或 .gist_token 文件）")
        return {}

    cfg = load_config()
    changed = False
    for key in UPLOAD_FILES:
        result = upload_file(token, key, cfg)
        if result:
            cfg[key] = result
            changed = True

    if changed:
        save_config(cfg)
        print(f"已保存 Gist 配置到 {GIST_CONFIG_FILE.name}")
    return cfg


def main():
    cfg = upload_all()
    if not cfg:
        sys.exit(1)
    print("\n=== Gist URLs ===")
    for key, entry in cfg.items():
        print(f"{key:8s} -> {entry.get('raw_url')}")


if __name__ == "__main__":
    main()
