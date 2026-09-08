# proxy

用本地 [subconverter](https://github.com/tindy2013/subconverter) 合并多订阅，生成 Clash / Loon 配置，可选上传到 GitHub Gist，并提供简易 Web 面板。

## 功能

- 从 `subscriptions.txt` 拉取多个订阅并转换
- 合并本地节点（`casefarm.yaml`）
- 按地区填充代理组（`group.txt`），生成 `merged_config.yaml` / `loon_config.conf`
- 可选上传到 Gist（`upload_to_gist.py`）
- Web 面板编辑配置并一键运行（`web_server.py`）

## 快速开始

### 1. 依赖

```bash
pip install -r requirements.txt
```

### 2. 本地配置（勿提交）

```bash
copy subscriptions.txt.example subscriptions.txt
copy casefarm.yaml.example casefarm.yaml
# 编辑上面两个文件，填入真实订阅与本地节点
```

Gist 上传（可选）：

```bash
# 任选其一：环境变量，或项目根目录 .gist_token（单行 PAT）
set GITHUB_TOKEN=ghp_xxx
```

### 3. 安装并启动 subconverter

```bash
setup_subconverter.bat
# 或之后单独启动：
start_subconverter.bat
```

服务默认：`http://localhost:25500`

### 4. 生成配置

```bash
python merge_proxy_config.py
```

输出：

- `merged_config.yaml` — Clash
- `loon_config.conf` — Loon

### 5. Web 面板（可选）

```bash
start_web.bat
# 浏览器打开 http://localhost:8080
```

## 仓库里跟踪什么

| 跟踪 | 忽略（本地私密 / 生成物） |
|------|---------------------------|
| `merge_proxy_config.py`、`web_server.py`、`upload_to_gist.py` 等源码 | `subscriptions.txt`、`casefarm.yaml`、`.gist_token`、`gist_config.json` |
| `group.txt`、`RuleList.txt`、`pref.ini` | `loon_config.conf`、`merged_config.yaml`、调试 yaml |
| `*.bat`、`*.example`、`requirements.txt` | `subconverter/`、`casefarm_repo/`、`__pycache__/` |

## 主要文件

- `merge_proxy_config.py` — 主流程：转换、注入 anytls、写 Loon/Clash
- `group.txt` — subconverter 自定义代理组
- `RuleList.txt` — 规则集列表
- `pref.ini` — subconverter 外部配置
- `upload_to_gist.py` — 上传生成结果到 Gist
- `web_server.py` — 本地管理面板

## 注意

- 不要把含节点密码、订阅 token、GitHub PAT 的文件推到公开仓库。
- `subconverter/` 需本机安装，不纳入版本库。
