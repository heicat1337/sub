#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载YAML配置文件并合并本地代理配置
"""

import sys
import os
import shutil

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
import urllib3
import yaml
import re
import base64
from pathlib import Path
from typing import Dict, List, Any
import argparse
import subprocess
from urllib.parse import quote, urlparse, parse_qs, unquote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SUBSCRIPTIONS_FILE = 'subscriptions.txt'

# 本地转换配置文件
LOCAL_CONVERTER_CONFIG = 'pref.ini'
# 本地subconverter地址
SUBCONVERTER_URL = 'http://localhost:25500/sub'
SUBCONVERTER_DIR = 'subconverter'

REGION_GROUP_PATTERNS = [
    ('HK 🇭🇰', r'.*(香港|HK).*'),
    ('TW 🇨🇳', r'.*(台湾|台灣|TW).*'),
    ('KR 🇰🇷', r'.*(韩国|KR).*'),
    ('JP 🇯🇵', r'.*(日本|东京|大阪|JP).*'),
    ('SG 🇸🇬', r'.*(新加坡|SG).*'),
    ('AU 🇦🇺', r'.*(澳大利亚|新西兰|悉尼|墨尔本|奥克兰|Oceania|AU).*'),
    ('RU 🇷🇺', r'.*(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯).*'),
    ('EU 🇪🇺', r'^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|欧洲|德国|英国|荷兰|法国|意大利|乌克兰|卢森堡|摩尔多瓦|爱尔兰|芬兰|以色列|南非).*'),
    ('CA 🇨🇦', r'.*(多伦多|加拿大|CA).*'),
    ('NA 🇺🇲', r'.*(硅谷|西雅图|美国|US).*'),
]


def parse_subscription_line(line: str, index: int) -> Dict[str, str] | None:
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    parts = line.split(maxsplit=1)
    url = parts[0]
    label = ''
    if len(parts) > 1:
        tail = parts[1].strip()
        if tail.startswith('#'):
            label = tail[1:].strip()
    return {'url': url, 'label': label or f'订阅{index}'}


def load_subscription_entries(file_path: str = SUBSCRIPTIONS_FILE) -> List[Dict[str, str]]:
    """从文件加载订阅链接和行尾标签。标签用于匹配 group.txt 里的代理组前缀。"""
    try:
        entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for raw in f:
                entry = parse_subscription_line(raw, len(entries))
                if entry:
                    entries.append(entry)
        return entries
    except FileNotFoundError:
        print(f"错误: 订阅文件 {file_path} 不存在")
        print(f"请创建 {file_path} 文件，每行一个订阅链接")
        sys.exit(1)


def make_group_patterns(label: str, include_low: bool = False) -> Dict[str, str]:
    patterns = {label: r'.*'}
    for suffix, pattern in REGION_GROUP_PATTERNS:
        patterns[f'{label}{suffix}'] = pattern
    if include_low:
        patterns['low'] = LOW_RATE_PATTERN
    return patterns


def load_subscriptions(file_path: str = SUBSCRIPTIONS_FILE) -> List[str]:
    """从文件加载订阅链接，支持行尾 ` #标签` 注释"""
    return [entry['url'] for entry in load_subscription_entries(file_path)]


def build_converter_url(subscriptions: List[str], config_path: str = None) -> str:
    """构建订阅转换URL（使用本地subconverter）"""
    # 将订阅链接用|分隔并URL编码
    encoded_subs = quote('|'.join(subscriptions))

    # 构建本地subconverter URL
    url = f"{SUBCONVERTER_URL}?target=clash&url={encoded_subs}"

    # 使用配置文件名（subconverter会在自己目录下查找）
    if config_path:
        url += f"&config={quote('config/' + os.path.basename(config_path))}"

    # 添加其他参数
    url += "&emoji=true&list=false&sort=true&udp=true&tfo=false&scv=false&append_type=false&fdn=false&new_name=false&dual=false&dns=fake"

    return url


def sync_subconverter_config() -> None:
    """同步 subconverter 运行时会读取的配置文件。

    subconverter 解析 `!!import:group.txt` 时使用的是自己的工作目录，不是项目根目录。
    如果不同步，生成配置会继续使用 subconverter/group.txt 里的旧代理组。
    """
    sub_dir = Path(SUBCONVERTER_DIR)
    config_dir = sub_dir / 'config'
    if not sub_dir.exists():
        print(f"警告: 未找到 {SUBCONVERTER_DIR} 目录，跳过 subconverter 配置同步")
        return
    config_dir.mkdir(parents=True, exist_ok=True)

    copies = [
        (Path('group.txt'), sub_dir / 'group.txt'),
        (Path('group.txt'), config_dir / 'group.txt'),
        (Path('RuleList.txt'), sub_dir / 'RuleList.txt'),
        (Path('RuleList.txt'), config_dir / 'RuleList.txt'),
        (Path(LOCAL_CONVERTER_CONFIG), sub_dir / LOCAL_CONVERTER_CONFIG),
        (Path(LOCAL_CONVERTER_CONFIG), config_dir / LOCAL_CONVERTER_CONFIG),
    ]
    for src, dst in copies:
        if not src.exists():
            print(f"警告: 未找到 {src}，跳过同步到 {dst}")
            continue
        shutil.copyfile(src, dst)
    print("已同步 subconverter 配置文件: group.txt / pref.ini / RuleList.txt")


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """加载YAML文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 不存在")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"错误: 解析YAML文件失败 - {e}")
        sys.exit(1)


def download_yaml(url: str, output_path: str = None) -> Dict[str, Any]:
    """从URL下载YAML配置文件"""
    try:
        print(f"正在下载配置文件: {url}")
        # subconverter 首次请求会拉取 rule_base 模板和全部 ruleset，冷启动约需 25-30s，
        # 30s 超时经常刚好卡在边界导致 Read timed out，这里放宽到 120s。
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        # 保存原始响应用于调试
        with open('debug_response.yaml', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"原始响应已保存到 debug_response.yaml，大小: {len(response.text)} 字节")

        # 保存下载的文件（如果指定了输出路径）
        if output_path:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"配置文件已保存到: {output_path}")

        # 解析YAML内容
        config = yaml.safe_load(response.text)

        # 转换键名格式（处理 Proxy/Proxy Group/Rule 格式）
        if 'Proxy' in config:
            config['proxies'] = config.pop('Proxy')
        if 'Proxy Group' in config:
            config['proxy-groups'] = config.pop('Proxy Group')
        if 'Rule' in config:
            config['rules'] = config.pop('Rule')

        return config or {}
    except requests.exceptions.RequestException as e:
        print(f"错误: 下载配置文件失败 - {e}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"错误: 解析下载的YAML文件失败 - {e}")
        sys.exit(1)


def extract_special_proxies_by_source(
    subscriptions: List[str],
    exclude_hosts: tuple = ('em.mesl.cloud', 'flag=anytls'),
) -> Dict[str, List[Dict[str, Any]]]:
    """按订阅源提取 subconverter 不支持/过滤掉的代理（vless 等）

    使用 clash.meta UA 访问订阅，绕过按 UA 过滤 meta-only 节点的机场（如 bocchi）。
    `exclude_hosts` 中匹配的订阅会被跳过（由专用函数处理，避免重复）。
    """
    SPECIAL_TYPES = {'vless'}
    headers = {'User-Agent': 'clash.meta'}
    result: Dict[str, List[Dict[str, Any]]] = {}
    for sub_url in subscriptions:
        if any(h in sub_url for h in exclude_hosts):
            continue
        try:
            response = requests.get(sub_url, timeout=10, headers=headers)
            response.raise_for_status()
            config = yaml.safe_load(response.text)
            if isinstance(config, dict) and 'proxies' in config:
                specials = [p for p in config['proxies'] if p.get('type') in SPECIAL_TYPES]
                if specials:
                    result[sub_url] = specials
        except Exception as e:
            print(f"警告: 提取特殊代理失败 ({sub_url}): {e}")
    return result


def merge_proxies(downloaded_config: Dict[str, Any], local_config: Dict[str, Any]) -> Dict[str, Any]:
    """合并代理配置"""
    # 获取本地代理列表
    local_proxies = local_config.get('proxies', [])
    if not local_proxies:
        print("警告: casefarm.yaml 中没有找到代理配置")
        return downloaded_config
    
    # 获取下载配置文件中的代理列表
    downloaded_proxies = downloaded_config.get('proxies', [])
    
    # 创建代理名称集合，用于去重
    existing_proxy_names = {proxy.get('name') for proxy in downloaded_proxies if proxy.get('name')}
    
    # 合并代理列表
    merged_proxies = downloaded_proxies.copy()
    added_count = 0
    
    for local_proxy in local_proxies:
        proxy_name = local_proxy.get('name')
        if proxy_name and proxy_name not in existing_proxy_names:
            merged_proxies.append(local_proxy)
            existing_proxy_names.add(proxy_name)
            added_count += 1
    
    downloaded_config['proxies'] = merged_proxies
    print(f"成功添加 {added_count} 个本地代理到配置文件")
    
    # 更新proxy-groups，将本地代理添加到选择组
    proxy_groups = downloaded_config.get('proxy-groups', [])
    local_proxy_names = [p.get('name') for p in local_proxies if p.get('name')]
    
    # 如果本地配置中有proxy-groups，可以合并
    local_proxy_groups = local_config.get('proxy-groups', [])
    if local_proxy_groups:
        # 查找或创建本地代理组
        for local_group in local_proxy_groups:
            group_name = local_group.get('name')
            # 查找是否存在同名组
            existing_group = None
            for group in proxy_groups:
                if group.get('name') == group_name:
                    existing_group = group
                    break
            
            if existing_group:
                # 如果组存在，合并代理列表
                existing_proxies = existing_group.get('proxies', [])
                for proxy_name in local_proxy_names:
                    if proxy_name not in existing_proxies:
                        existing_proxies.append(proxy_name)
            else:
                # 如果组不存在，添加新组
                proxy_groups.append(local_group)
    
    # 将所有本地代理添加到第一个select类型的组（如果存在）
    if proxy_groups and local_proxy_names:
        for group in proxy_groups:
            if group.get('type') == 'select':
                group_proxies = group.get('proxies', [])
                for proxy_name in local_proxy_names:
                    if proxy_name not in group_proxies:
                        group_proxies.append(proxy_name)
                break
    
    downloaded_config['proxy-groups'] = proxy_groups
    
    # 合并规则（rules）
    local_rules = local_config.get('rules', [])
    if local_rules:
        downloaded_rules = downloaded_config.get('rules', [])
        # 将本地规则添加到规则列表的开头（优先级更高）
        # 去重：检查本地规则是否已存在
        existing_rules = set()
        for rule in downloaded_rules:
            # 将规则转换为字符串以便比较（处理列表和字符串两种格式）
            rule_str = str(rule) if isinstance(rule, list) else rule
            existing_rules.add(rule_str)
        
        added_rules = []
        for local_rule in local_rules:
            rule_str = str(local_rule) if isinstance(local_rule, list) else local_rule
            if rule_str not in existing_rules:
                downloaded_rules.insert(0, local_rule)  # 插入到开头
                existing_rules.add(rule_str)
                added_rules.append(local_rule)
        
        downloaded_config['rules'] = downloaded_rules
        if added_rules:
            print(f"成功添加 {len(added_rules)} 条本地规则到配置文件")
    
    return downloaded_config


def save_yaml(config: Dict[str, Any], output_path: str):
    """保存YAML配置文件"""
    try:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"合并后的配置文件已保存到: {output_path}")
    except Exception as e:
        print(f"错误: 保存配置文件失败 - {e}")
        sys.exit(1)


def _anytls_to_loon(proxy: Dict[str, Any]) -> str:
    """anytls dict → Loon 行。type 必须是 AnyTLS（驼峰），密码是第 4 位带引号的位置参数，否则握手会超时"""
    parts = [
        f"{proxy['name']} = AnyTLS",
        str(proxy['server']),
        str(proxy['port']),
        f'"{proxy.get("password", "")}"',
    ]
    if proxy.get('sni'):
        parts.append(f"sni={proxy['sni']}")
    parts.append(f"skip-cert-verify={'true' if proxy.get('skip-cert-verify') else 'false'}")
    if proxy.get('udp', True):
        parts.append("udp=true")
    parts.append("block-quic=false")
    return ','.join(parts)


def _vless_to_loon(proxy: Dict[str, Any]) -> str:
    """将 vless dict（Clash 格式）转为 Loon 一行格式，支持 reality / tls"""
    parts = [
        f"{proxy['name']} = vless",
        str(proxy['server']),
        str(proxy['port']),
        f"username={proxy.get('uuid', '')}",
    ]
    network = proxy.get('network', 'tcp')
    parts.append(f"transport={network}")

    reality = proxy.get('reality-opts')
    if reality:
        parts.append("security=reality")
        if reality.get('public-key'):
            parts.append(f"public-key={reality['public-key']}")
        if reality.get('short-id'):
            parts.append(f"short-id={reality['short-id']}")
    elif proxy.get('tls'):
        parts.append("security=tls")

    sni = proxy.get('servername') or proxy.get('sni')
    if sni:
        parts.append(f"sni={sni}")
    if proxy.get('flow'):
        parts.append(f"flow={proxy['flow']}")
    if proxy.get('client-fingerprint'):
        parts.append(f"client-fingerprint={proxy['client-fingerprint']}")
    if network == 'ws':
        ws = proxy.get('ws-opts') or {}
        if ws.get('path'):
            parts.append(f"path={ws['path']}")
        host = (ws.get('headers') or {}).get('Host')
        if host:
            parts.append(f"host={host}")

    parts.append(f"skip-cert-verify={'true' if proxy.get('skip-cert-verify') else 'false'}")
    if proxy.get('udp', True):
        parts.append("udp=true")
    return ','.join(parts)


def _proxy_to_loon(proxy: Dict[str, Any]) -> str | None:
    t = proxy.get('type')
    if t == 'anytls':
        return _anytls_to_loon(proxy)
    if t == 'vless':
        return _vless_to_loon(proxy)
    return None


def _split_loon_group(line: str):
    """拆解 Loon 代理组行。返回 (name, gtype, nodes, options) 或 None"""
    if '=' not in line:
        return None
    head, rest = line.split('=', 1)
    name = head.strip()
    tokens = [p.strip() for p in rest.strip().split(',') if p.strip()]
    if not tokens:
        return None
    gtype = tokens[0]
    nodes, options = [], []
    for tok in tokens[1:]:
        (options if '=' in tok else nodes).append(tok)
    return name, gtype, nodes, options


def _join_loon_group(name: str, gtype: str, nodes: List[str], options: List[str]) -> str:
    return f"{name} = {','.join([gtype, *nodes, *options])}"


def inject_proxies_to_loon(
    loon_text: str,
    proxies: List[Dict[str, Any]],
    group_patterns: Dict[str, str],
    label: str = '',
) -> str:
    """把代理节点（anytls / vless）注入 Loon 配置：追加到 [Proxy] 段 + 更新对应分组。

    若 [Proxy] 中已经有同名 / 同 (server,port) 的行（subconverter 输出但 scv=false
    把 skip-cert-verify 强制成 false），用本函数收到的原始 proxy dict 重新生成行
    并就地覆写，保留 subconverter 命名（可能因 emoji=true geoip 改过国旗）。
    """
    if not proxies:
        return loon_text
    lines = loon_text.splitlines()

    # 找 [Proxy] 段范围
    proxy_section_start = None
    proxy_section_end = None
    in_proxy = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s == '[Proxy]':
            in_proxy = True
            proxy_section_start = i + 1
            continue
        if in_proxy and s.startswith('[') and s.endswith(']'):
            proxy_section_end = i
            break
    if proxy_section_end is None or proxy_section_start is None:
        print("警告: Loon 配置中未找到 [Proxy] 段，跳过注入")
        return loon_text

    # 索引现有节点：名字 → 行号；(server,port) → 行号
    name_to_idx: Dict[str, int] = {}
    addr_to_idx: Dict[tuple, int] = {}
    for idx, line in enumerate(lines[proxy_section_start:proxy_section_end], start=proxy_section_start):
        if '=' not in line or line.strip().startswith('#'):
            continue
        name, _, body = line.partition('=')
        name_to_idx[name.strip()] = idx
        fields = [f.strip() for f in body.strip().split(',')]
        # AnyTLS / trojan 等都是 type,host,port,... 位置参数
        if len(fields) >= 3:
            addr_to_idx[(fields[1], fields[2])] = idx

    new_lines = []
    new_names = []
    replaced = 0
    for p in proxies:
        loon_line = _proxy_to_loon(p)
        if loon_line is None:
            continue
        addr_key = (str(p.get('server')), str(p.get('port')))
        idx = name_to_idx.get(p['name'])
        if idx is None:
            idx = addr_to_idx.get(addr_key)
        if idx is not None:
            # 覆写参数，保留 subconverter 那边的名字
            head = lines[idx].split('=', 1)[0]
            body = loon_line.split('=', 1)[1]
            lines[idx] = f'{head}={body}'
            new_names.append(head.strip())
            replaced += 1
        else:
            new_lines.append(loon_line)
            new_names.append(p['name'])
            name_to_idx[p['name']] = -1  # 占位避免同批重复
            addr_to_idx[addr_key] = -1

    tag = f'[{label}]' if label else ''
    print(f'{tag} Loon 新增 {len(new_lines)} 节点, 覆写 {replaced} 节点参数, 共参与分组 {len(new_names)}')
    lines = lines[:proxy_section_end] + new_lines + lines[proxy_section_end:]

    # 分组匹配应覆盖 [Proxy] 段已有节点；subconverter 的 loon 输出不会填充
    # !!GROUPID=0!! 过滤器，若只匹配本次注入的 new_names，MESL 等区域组会一直是 REJECT。
    all_proxy_names = []
    for line in lines[proxy_section_start:proxy_section_end]:
        if '=' in line and not line.strip().startswith('#'):
            all_proxy_names.append(line.split('=', 1)[0].strip())
    candidate_names = list(dict.fromkeys([*all_proxy_names, *new_names]))

    # 更新分组
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith('#') or s.startswith('['):
            continue
        parsed = _split_loon_group(line)
        if not parsed:
            continue
        name, gtype, nodes, options = parsed
        pattern = group_patterns.get(name)
        if not pattern:
            continue
        matched = [n for n in candidate_names if re.search(pattern, n)]
        if not matched:
            continue
        # 剥占位
        if 'DIRECT' in nodes:
            nodes.remove('DIRECT')
        had_reject = nodes == ['REJECT']
        if had_reject:
            nodes = []
        added_here = 0
        for n in matched:
            if n not in nodes:
                nodes.append(n)
                added_here += 1
        if not nodes and had_reject:
            nodes = ['REJECT']
        lines[i] = _join_loon_group(name, gtype, nodes, options)
        if added_here:
            print(f'  Loon {name}: +{added_here}')

    return '\n'.join(lines) + ('\n' if loon_text.endswith('\n') else '')


def inject_casefarm_to_loon(loon_text: str, local_config: Dict[str, Any]) -> str:
    """把 casefarm 本地节点注入 Loon：追加到 [Proxy] 段，并按本地 proxy-groups 精确节点名加到 Loon 同名组"""
    local_proxies = local_config.get('proxies', [])
    local_groups = local_config.get('proxy-groups', [])
    if not local_proxies:
        return loon_text
    lines = loon_text.splitlines()

    proxy_section_start = None
    proxy_section_end = None
    in_proxy = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s == '[Proxy]':
            in_proxy = True
            proxy_section_start = i + 1
            continue
        if in_proxy and s.startswith('[') and s.endswith(']'):
            proxy_section_end = i
            break
    if proxy_section_end is None or proxy_section_start is None:
        print("警告: Loon 配置中未找到 [Proxy] 段，跳过 casefarm 注入")
        return loon_text

    existing_names = set()
    for line in lines[proxy_section_start:proxy_section_end]:
        if '=' in line and not line.strip().startswith('#'):
            existing_names.add(line.split('=', 1)[0].strip())

    new_lines = []
    for p in local_proxies:
        name = p.get('name')
        if not name or name in existing_names:
            continue
        loon_line = _proxy_to_loon(p)
        if loon_line is None:
            print(f"  跳过不支持的 casefarm 节点类型: {p.get('type')} ({name})")
            continue
        new_lines.append(loon_line)
        existing_names.add(name)
    print(f'[casefarm] Loon 新增 {len(new_lines)} 节点')
    lines = lines[:proxy_section_end] + new_lines + lines[proxy_section_end:]

    group_to_nodes = {g['name']: g.get('proxies', []) for g in local_groups if g.get('name')}
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith('#') or s.startswith('['):
            continue
        parsed = _split_loon_group(line)
        if not parsed:
            continue
        name, gtype, nodes, options = parsed
        casefarm_nodes = group_to_nodes.get(name)
        if not casefarm_nodes:
            continue
        if 'DIRECT' in nodes:
            nodes.remove('DIRECT')
        had_reject = nodes == ['REJECT']
        if had_reject:
            nodes = []
        added_here = 0
        for n in casefarm_nodes:
            if n not in nodes:
                nodes.append(n)
                added_here += 1
        if not nodes and had_reject:
            nodes = ['REJECT']
        lines[i] = _join_loon_group(name, gtype, nodes, options)
        if added_here:
            print(f'  Loon {name}: +{added_here} (casefarm)')

    return '\n'.join(lines) + ('\n' if loon_text.endswith('\n') else '')


def _clash_rule_to_loon(rule: Any) -> str | None:
    if not isinstance(rule, str):
        return None
    line = rule.strip()
    if not line or line.startswith('#'):
        return None
    if line.startswith('MATCH,'):
        return 'FINAL,' + line.split(',', 1)[1]
    return line


def apply_rules_to_loon(loon_text: str, rules: List[Any]) -> str:
    """用 Clash/YAML 侧已经生成好的 rules 重写 Loon [Rule] 段。"""
    loon_rules = []
    seen = set()
    for rule in rules:
        line = _clash_rule_to_loon(rule)
        if line and line not in seen:
            loon_rules.append(line)
            seen.add(line)
    if not loon_rules:
        print("警告: merged_config 中没有可写入 Loon 的规则，跳过 [Rule] 同步")
        return loon_text

    lines = loon_text.splitlines()
    rule_start = None
    rule_end = None
    for i, line in enumerate(lines):
        if line.strip() == '[Rule]':
            rule_start = i
            break
    if rule_start is None:
        insert_at = len(lines)
        lines.extend(['', '[Rule]', *loon_rules])
        print(f"已向 Loon 新增 [Rule] 段: {len(loon_rules)} 条")
        return '\n'.join(lines) + ('\n' if loon_text.endswith('\n') else '')

    rule_end = len(lines)
    for i in range(rule_start + 1, len(lines)):
        s = lines[i].strip()
        if s.startswith('[') and s.endswith(']'):
            rule_end = i
            break

    replacement = ['[Rule]', *loon_rules, '']
    lines = lines[:rule_start] + replacement + lines[rule_end:]
    print(f"已同步 Loon [Rule] 段: {len(loon_rules)} 条")
    return '\n'.join(lines) + ('\n' if loon_text.endswith('\n') else '')


def generate_loon_config(subscriptions: List[str]) -> str:
    """生成 Loon 配置"""
    sub_url = '|'.join(subscriptions)
    params = {
        'target': 'loon',
        'url': sub_url,
        'config': 'config/' + LOCAL_CONVERTER_CONFIG
    }
    try:
        response = requests.get(SUBCONVERTER_URL, params=params, timeout=120)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"生成 Loon 配置失败: {e}")
        return None


def push_to_gist():
    """将 merged_config.yaml 和 loon_config.conf 分别上传到两个 Gist"""
    try:
        import upload_to_gist
        result = upload_to_gist.upload_all()
        if result:
            print("已上传到 Gist！")
        else:
            print("Gist 上传未产生结果（检查 token 和文件）")
    except Exception as e:
        print(f"Gist 上传失败: {e}")


# 低倍率节点识别模式：匹配 [0.3X] / [0.3x] / x0.2 / 0.3x / 0.3× 等
LOW_RATE_PATTERN = r'(?i)0\.\d+\s*[xX×]|[xX×]\s?0\.\d+|\[0\.\d+[xX×]?\]'


DORIYANET_GROUP_PATTERNS = {
    'doriyanet':        r'.*',
    'doriyanetHK 🇭🇰': r'.*(香港|HK).*',
    'doriyanetTW 🇨🇳': r'.*(台湾|台灣|TW).*',
    'doriyanetKR 🇰🇷': r'.*(韩国|KR).*',
    'doriyanetJP 🇯🇵': r'.*(日本|JP).*',
    'doriyanetSG 🇸🇬': r'.*(新加坡|SG).*',
    'doriyanetAU 🇦🇺': r'.*(澳大利亚|Oceania|AU).*',
    'doriyanetRU 🇷🇺': r'.*(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯).*',
    'doriyanetEU 🇪🇺': r'^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|欧洲|德国|英国|荷兰|法国|意大利).*',
    'doriyanetCA 🇨🇦': r'.*(多伦多|加拿大|CA).*',
    'doriyanetNA 🇺🇲': r'.*(硅谷|西雅图|美国|US).*',
    'low':              LOW_RATE_PATTERN,
}


BOCCHI_GROUP_PATTERNS = {
    'bocchi':        r'.*',
    'bocchiHK 🇭🇰': r'.*(香港|HK).*',
    'bocchiTW 🇨🇳': r'.*(台湾|台灣|TW).*',
    'bocchiKR 🇰🇷': r'.*(韩国|KR).*',
    'bocchiJP 🇯🇵': r'.*(日本|JP).*',
    'bocchiSG 🇸🇬': r'.*(新加坡|SG).*',
    'bocchiAU 🇦🇺': r'.*(澳大利亚|Oceania|AU).*',
    'bocchiRU 🇷🇺': r'.*(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯).*',
    'bocchiEU 🇪🇺': r'^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|欧洲|德国|英国|荷兰|法国|意大利).*',
    'bocchiCA 🇨🇦': r'.*(多伦多|加拿大|CA).*',
    'bocchiNA 🇺🇲': r'.*(美国|US).*',
    'low':           LOW_RATE_PATTERN,
}


MESL_GROUP_PATTERNS = {
    'MESL':        r'.*',
    'MESLHK 🇭🇰': r'.*(香港|HK).*',
    'MESLTW 🇨🇳': r'.*(台湾|台灣|TW).*',
    'MESLKR 🇰🇷': r'.*(韩国|KR).*',
    'MESLJP 🇯🇵': r'.*(日本|JP).*',
    'MESLSG 🇸🇬': r'.*(新加坡|SG).*',
    'MESLAU 🇦🇺': r'.*(澳大利亚|新西兰|悉尼|墨尔本|奥克兰|Oceania|AU).*',
    'MESLRU 🇷🇺': r'.*(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯).*',
    'MESLEU 🇪🇺': r'^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|欧洲|德国|英国|荷兰|法国|意大利|乌克兰|卢森堡|摩尔多瓦|爱尔兰|芬兰|以色列|南非).*',
    'MESLCA 🇨🇦': r'.*(多伦多|加拿大|CA).*',
    'MESLNA 🇺🇲': r'.*(硅谷|西雅图|美国|US).*',
    'low':         LOW_RATE_PATTERN,
}


# dlercloud：已切到 anytls 协议，subconverter 可以正常拉取，但 scv=false 会把
# skip-cert-verify 强制成 false。机场实际签的证书要求 scv=true，所以照 雨燕云
# 的套路从原始 YAML 回填真实 scv。
DLERCLOUD_GROUP_PATTERNS = {
    'dlercloud':        r'.*',
    'dlercloudHK 🇭🇰': r'.*(香港|HK).*',
    'dlercloudTW 🇨🇳': r'.*(台湾|台灣|TW).*',
    'dlercloudKR 🇰🇷': r'.*(韩国|KR).*',
    'dlercloudJP 🇯🇵': r'.*(日本|东京|大阪|JP).*',
    'dlercloudSG 🇸🇬': r'.*(新加坡|SG).*',
    'dlercloudAU 🇦🇺': r'.*(澳大利亚|新西兰|Oceania|AU).*',
    'dlercloudRU 🇷🇺': r'.*(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯).*',
    'dlercloudEU 🇪🇺': r'^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|欧洲|德国|英国|荷兰|法国|意大利|爱尔兰|西班牙).*',
    'dlercloudCA 🇨🇦': r'.*(多伦多|加拿大|CA).*',
    'dlercloudNA 🇺🇲': r'.*(美国|US).*',
    'low':              LOW_RATE_PATTERN,
}


# 雨燕云：subconverter 的 loon target 不识别 anytls，会整批丢弃；
# 这里直接从订阅的 Clash YAML 拉 anytls 节点，再走 Loon 注入。
YUYAN_GROUP_PATTERNS = {
    '雨燕云':        r'.*',
    '雨燕云HK 🇭🇰': r'.*(香港|HK).*',
    '雨燕云TW 🇨🇳': r'.*(台湾|台灣|TW).*',
    '雨燕云KR 🇰🇷': r'.*(韩国|KR).*',
    '雨燕云JP 🇯🇵': r'.*(日本|JP).*',
    '雨燕云SG 🇸🇬': r'.*(新加坡|SG).*',
    '雨燕云AU 🇦🇺': r'.*(澳大利亚|AU).*',
    '雨燕云EU 🇪🇺': r'^(?!.*?(莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯)).*(Europe|乌克兰|卢森堡|德国|意大利|摩尔多瓦|爱尔兰|芬兰|英国|荷兰|以色列|南非).*',
    '雨燕云NA 🇺🇲': r'.*(美国|US).*',
}


def _parse_anytls_uri(uri: str) -> Dict[str, Any]:
    try:
        uri = uri.strip()
        name = 'anytls'
        if '#' in uri:
            uri, frag = uri.rsplit('#', 1)
            name = unquote(frag).strip()
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        def p(key, default=None):
            return params.get(key, [default])[0]

        proxy = {
            'name': name,
            'type': 'anytls',
            'server': parsed.hostname,
            'port': parsed.port,
            'password': unquote(parsed.username or ''),
            'udp': True,
        }
        if p('insecure', '0') == '1':
            proxy['skip-cert-verify'] = True
        sni = p('sni')
        if sni:
            proxy['sni'] = sni
        alpn = p('alpn')
        if alpn:
            proxy['alpn'] = [a for a in alpn.split(',') if a]
        fp = p('fp')
        if fp:
            proxy['client-fingerprint'] = fp
        return proxy
    except Exception as e:
        print(f'警告: 解析 anytls URI 失败: {e}')
        return None


def fetch_b64_subscription(url: str, scheme: str, parser, label: str, log_empty: bool = True) -> List[Dict[str, Any]]:
    """下载并解析 Base64 编码的 URI 订阅（通用：vless / anytls / ...）"""
    prefix = scheme + '://'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        decoded = base64.b64decode(response.text.strip() + '==').decode('utf-8')
        proxies = []
        for line in decoded.splitlines():
            line = line.strip()
            if line.startswith(prefix):
                proxy = parser(line)
                if proxy:
                    proxies.append(proxy)
        if proxies or log_empty:
            print(f'从 {label} 订阅解析到 {len(proxies)} 个 {scheme} 节点')
        return proxies
    except Exception as e:
        print(f'警告: 解析 {label} 订阅失败: {e}')
        return []


def fetch_b64_anytls_subscription(url: str) -> List[Dict[str, Any]]:
    return fetch_b64_subscription(url, 'anytls', _parse_anytls_uri, 'MESL')


def fetch_yaml_proxies_by_type(url: str, types: set, label: str, verify: bool = True, log_empty: bool = True) -> List[Dict[str, Any]]:
    """直接拉 Clash YAML 订阅，按 type 过滤节点。雨燕云用自签证书所以 verify 可关。"""
    headers = {'User-Agent': 'clash.meta'}
    try:
        response = requests.get(url, timeout=15, headers=headers, verify=verify)
        response.raise_for_status()
        config = yaml.safe_load(response.text) or {}
        proxies = [p for p in config.get('proxies', []) if p.get('type') in types]
        if proxies or log_empty:
            print(f'从 {label} 订阅解析到 {len(proxies)} 个 {"/".join(sorted(types))} 节点')
        return proxies
    except Exception as e:
        print(f'警告: 解析 {label} 订阅失败: {e}')
        return []


def assign_proxies_to_groups(
    config: Dict[str, Any],
    proxies: List[Dict[str, Any]],
    group_patterns: Dict[str, str],
    label: str,
) -> None:
    """将节点加入 proxies 列表并按正则模式分配到对应代理组"""
    if not proxies:
        return
    existing_names = {p.get('name') for p in config.get('proxies', [])}
    added = []
    candidate_names = []
    for proxy in proxies:
        name = proxy.get('name')
        if not name:
            continue
        candidate_names.append(name)
        if name not in existing_names:
            config.setdefault('proxies', []).append(proxy)
            existing_names.add(name)
            added.append(name)
    print(f'添加了 {len(added)} 个 {label} 节点到 proxies')

    groups_by_name = {g['name']: g for g in config.get('proxy-groups', [])}
    for group_name, pattern in group_patterns.items():
        group = groups_by_name.get(group_name)
        if not group:
            continue
        group_proxies = group.setdefault('proxies', [])
        # 剥掉占位：DIRECT（subconverter 在空 select 组里加）/ REJECT（空 url-test 组里加）
        if 'DIRECT' in group_proxies:
            group_proxies.remove('DIRECT')
        had_reject = group_proxies == ['REJECT']
        if had_reject:
            group_proxies.clear()
        added_here = 0
        for name in candidate_names:
            if re.search(pattern, name) and name not in group_proxies:
                group_proxies.append(name)
                added_here += 1
        if not group_proxies and had_reject:
            group_proxies.append('REJECT')
        print(f'  {group_name}: +{added_here}，共 {len(group_proxies)} 个节点')


def main():
    # 切换到脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description='从订阅链接下载配置并合并本地代理')
    parser.add_argument('-s', '--subscriptions', default=SUBSCRIPTIONS_FILE,
                       help=f'订阅链接文件路径（默认: {SUBSCRIPTIONS_FILE}）')
    parser.add_argument('-l', '--local', default='casefarm.yaml',
                       help='本地代理配置文件路径（默认: casefarm.yaml）')
    parser.add_argument('-o', '--output', default='merged_config.yaml',
                       help='输出文件路径（默认: merged_config.yaml）')
    parser.add_argument('--no-config', action='store_true',
                       help='不使用转换配置')

    args = parser.parse_args()

    # 加载订阅链接
    print(f"正在加载订阅链接: {args.subscriptions}")
    subscription_entries = load_subscription_entries(args.subscriptions)
    subscriptions = [entry['url'] for entry in subscription_entries]
    subscription_by_url = {entry['url']: entry for entry in subscription_entries}
    print(f"找到 {len(subscriptions)} 个订阅链接")

    # subconverter 会从自己的工作目录读取 config/pref.ini 和 !!import:group.txt。
    # 每次运行前同步，避免生成文件继续使用旧代理组。
    if not args.no_config:
        sync_subconverter_config()

    # 构建转换URL（使用本地配置文件）
    config_path = None if args.no_config else LOCAL_CONVERTER_CONFIG
    converter_url = build_converter_url(subscriptions, config_path)
    print(f"转换URL已生成")

    # 加载本地代理配置
    print(f"正在加载本地代理配置: {args.local}")
    local_config = load_yaml_file(args.local)

    # 下载远程配置文件
    downloaded_config = download_yaml(converter_url)

    # 调试输出
    print(f"下载的配置包含: {len(downloaded_config.get('proxies', []))} 个代理, {len(downloaded_config.get('proxy-groups', []))} 个代理组, {len(downloaded_config.get('rules', []))} 条规则")

    # 按 source label 累积的代理，供 Loon 注入阶段复用
    loon_injections: List[tuple] = []  # [(proxies, patterns, label), ...]

    # 提取 vless 等特殊代理（按来源分组 → 分派到各机场分组）
    print("正在从原始订阅提取 vless 代理...")
    specials_by_src = extract_special_proxies_by_source(subscriptions)
    if not specials_by_src:
        print("未找到 vless 代理")
    for src_url, src_proxies in specials_by_src.items():
        # 过滤掉 short-id 为 null 的 vless reality 节点
        filtered = []
        for p in src_proxies:
            if p.get('type') == 'vless':
                short_id = p.get('short-id') or (p.get('reality-opts') or {}).get('short-id')
                if short_id is None:
                    print(f"跳过 short-id 为 null 的 vless 代理: {p.get('name')}")
                    continue
            filtered.append(p)
        if not filtered:
            continue

        entry = subscription_by_url.get(src_url)
        label = entry['label'] if entry else None
        if not label:
            print(f"未找到订阅标签，跳过 vless 分组: {src_url}")
            continue
        patterns = make_group_patterns(label, include_low=True)
        assign_proxies_to_groups(downloaded_config, filtered, patterns, label)
        loon_injections.append((filtered, patterns, label))

    # 处理 MESL (Base64 anytls) 订阅
    mesl_url = next((s for s in subscriptions if 'em.mesl.cloud' in s or 'flag=anytls' in s), None)
    if mesl_url:
        print("正在解析 MESL 订阅...")
        mesl_proxies = fetch_b64_anytls_subscription(mesl_url)
        if mesl_proxies:
            assign_proxies_to_groups(downloaded_config, mesl_proxies, MESL_GROUP_PATTERNS, 'MESL')
            loon_injections.append((mesl_proxies, MESL_GROUP_PATTERNS, 'MESL'))

    # 处理 雨燕云 (Clash YAML, anytls 节点) 订阅 —— subconverter 的 loon target 会丢
    # anytls，所以直接抓原始 YAML 走 Loon 注入。clash 那边 subconverter 输出的节点
    # 被 scv=false 强制改成 skip-cert-verify: false，但雨燕云用 IP+SNI 自签证书，
    # 必须保留 true，所以用原始 YAML 的值回填。
    yuyan_url = next((s for s in subscriptions if '173.249.210.26' in s or 'yuyan' in s), None)
    if yuyan_url:
        print("正在解析 雨燕云 订阅...")
        yuyan_proxies = fetch_yaml_proxies_by_type(yuyan_url, {'anytls'}, '雨燕云', verify=False)
        if yuyan_proxies:
            # 按 (server, port) 配对：emoji=true 会按 geoip 改国旗（如 🇵🇰菲律宾→🇵🇭），
            # 名字会变，但 server+port 不会。
            yuyan_truth = {(p.get('server'), p.get('port')): p for p in yuyan_proxies}
            patched = 0
            for clash_proxy in downloaded_config.get('proxies', []):
                src = yuyan_truth.get((clash_proxy.get('server'), clash_proxy.get('port')))
                if src and src.get('skip-cert-verify') is not None:
                    clash_proxy['skip-cert-verify'] = src['skip-cert-verify']
                    patched += 1
            print(f"  回填 skip-cert-verify: {patched} 个 雨燕云 节点")
            loon_injections.append((yuyan_proxies, YUYAN_GROUP_PATTERNS, '雨燕云'))

    # 处理 dlercloud (Clash YAML, anytls 节点) 订阅 —— 同样的 scv 回填逻辑：
    # subconverter 输出的 anytls 节点会被 scv=false 强制改成 skip-cert-verify: false，
    # 但 dlercloud 的服务端要求 scv=true，需要从原始 YAML 回填到 clash + loon 两侧。
    dlercloud_url = next((s for s in subscriptions if 'oics.net' in s), None)
    if dlercloud_url:
        print("正在解析 dlercloud 订阅...")
        dler_proxies = fetch_yaml_proxies_by_type(dlercloud_url, {'anytls'}, 'dlercloud')
        if dler_proxies:
            dler_truth = {(p.get('server'), p.get('port')): p for p in dler_proxies}
            patched = 0
            for clash_proxy in downloaded_config.get('proxies', []):
                src = dler_truth.get((clash_proxy.get('server'), clash_proxy.get('port')))
                if src and src.get('skip-cert-verify') is not None:
                    clash_proxy['skip-cert-verify'] = src['skip-cert-verify']
                    patched += 1
            print(f"  回填 skip-cert-verify: {patched} 个 dlercloud 节点")
            loon_injections.append((dler_proxies, DLERCLOUD_GROUP_PATTERNS, 'dlercloud'))

    # 通用处理：对 subscriptions.txt 里的每个标签，尝试从原始 Clash YAML 提取 anytls 节点。
    # 新增订阅组（例如 ViKing）只要在 group.txt 中有同名分组，就会自动分派到对应组。
    processed_anytls_urls = {
        url for url in (mesl_url, yuyan_url, dlercloud_url) if url
    }
    for entry in subscription_entries:
        url = entry['url']
        label = entry['label']
        if url in processed_anytls_urls:
            continue
        print(f"正在解析 {label} 订阅中的 anytls 节点...")
        proxies = fetch_yaml_proxies_by_type(url, {'anytls'}, label, verify=False, log_empty=False)
        if not proxies:
            proxies = fetch_b64_subscription(url, 'anytls', _parse_anytls_uri, label, log_empty=False)
        if not proxies:
            print(f"  {label}: 未发现需要额外回填的 anytls 节点，普通节点由 subconverter 处理")
            continue
        truth = {(p.get('server'), p.get('port')): p for p in proxies}
        patched = 0
        for clash_proxy in downloaded_config.get('proxies', []):
            src = truth.get((clash_proxy.get('server'), clash_proxy.get('port')))
            if src and src.get('skip-cert-verify') is not None:
                clash_proxy['skip-cert-verify'] = src['skip-cert-verify']
                patched += 1
        print(f"  回填 skip-cert-verify: {patched} 个 {label} 节点")
        patterns = make_group_patterns(label)
        assign_proxies_to_groups(downloaded_config, proxies, patterns, label)
        loon_injections.append((proxies, patterns, label))

    # 合并代理配置
    print("正在合并代理配置...")
    merged_config = merge_proxies(downloaded_config, local_config)

    # 保存合并后的配置文件
    save_yaml(merged_config, args.output)

    # 生成 Loon 配置
    print("正在生成 Loon 配置...")
    loon_config = generate_loon_config(subscriptions)
    if loon_config:
        for proxies, patterns, label in loon_injections:
            print(f"正在向 Loon 注入 {label} 节点...")
            loon_config = inject_proxies_to_loon(loon_config, proxies, patterns, label)
        print("正在向 Loon 注入 casefarm 本地节点...")
        loon_config = inject_casefarm_to_loon(loon_config, local_config)
        print("正在同步 Loon 规则...")
        loon_config = apply_rules_to_loon(loon_config, merged_config.get('rules', []))
        with open('loon_config.conf', 'w', encoding='utf-8') as f:
            f.write(loon_config)
        print("Loon 配置已保存到: loon_config.conf")

    # 上传到 Gist
    push_to_gist()

    print("\n完成！")


if __name__ == '__main__':
    main()

