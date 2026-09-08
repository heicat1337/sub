import subprocess
import time
import re
import socket
import requests
import urllib3

urllib3.disable_warnings()

CONVERTER_HOST = '127.0.0.1'
CONVERTER_PORT = 25500
CONVERTER_URL = f'http://{CONVERTER_HOST}:{CONVERTER_PORT}/sub'

# subconverter 不识别 anytls 协议，针对包含 anytls 行的订阅做旁路注入
ANNOUNCEMENT_RE = re.compile(r'^(?:官网|请立即|ios设备|android设备|距离下次重置)')

# 订阅备注 → group.txt 里对应的分组前缀（大小写敏感）
TAG_TO_GROUP = {
    'MESL': 'mesl',
    'dlercloud': 'dlercloud',
    'doriyanet': 'doriyanet',
    'bocchi': 'bocchi',
    '雨燕云': '雨燕云',
}

# 地区匹配：跟 group.txt 里的正则保持一致
RU_RE = re.compile(r'莫斯科|圣彼得堡|哈巴罗夫斯克|俄罗斯')
EU_RE = re.compile(
    r'Europe|乌克兰|卢森堡|德国|意大利|摩尔多瓦|爱尔兰|芬兰|英国|荷兰|以色列|南非|'
    r'法国|奥地利|瑞士|捷克|匈牙利|波兰|希腊|挪威|瑞典|丹麦|比利时|葡萄牙|西班牙|'
    r'罗马尼亚|保加利亚|塞尔维亚|斯洛伐克|斯洛文尼亚|拉脱维亚|立陶宛|爱沙尼亚|冰岛|'
    r'马耳他|克罗地亚|乌拉圭|阿尔巴尼亚'
)
REGION_RES = [
    ('HK 🇭🇰', re.compile(r'香港|HK')),
    ('TW 🇨🇳', re.compile(r'台湾|台灣|TW')),
    ('KR 🇰🇷', re.compile(r'韩国|KR')),
    ('JP 🇯🇵', re.compile(r'日本|JP|东京|大阪')),
    ('SG 🇸🇬', re.compile(r'新加坡|SG')),
    ('AU 🇦🇺', re.compile(r'澳大利亚|新西兰|悉尼|墨尔本|奥克兰|Oceania')),
    ('CA 🇨🇦', re.compile(r'多伦多|加拿大')),
    ('NA 🇺🇲', re.compile(r'硅谷|西雅图|美国|US')),
]


def parse_subs():
    out = []
    with open('subscriptions.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            url, sep, tag = line.partition('#')
            out.append((url.strip(), tag.strip()))
    return out


def fetch_anytls_nodes(url, tag):
    """返回 [(name, line)]"""
    try:
        # 显式禁用系统代理：Windows 下 requests 会读 WinINET 经 Clash 出网，
        # 多数机场会因为源 IP 是代理而拒绝订阅请求
        r = requests.get(url, headers={'User-Agent': 'Loon/780'},
                         timeout=15, verify=False,
                         proxies={'http': '', 'https': ''})
        r.raise_for_status()
    except Exception as e:
        print(f'  [skip] {tag or url[:50]}: {e}')
        return []
    nodes = []
    for raw in r.text.splitlines():
        raw = raw.strip()
        if '=' not in raw:
            continue
        name, _, body = raw.partition('=')
        name = name.strip()
        body = body.strip()
        if not body.lower().startswith('anytls,'):
            continue
        if ANNOUNCEMENT_RE.search(name):
            continue
        fields = body.split(',')
        if len(fields) < 4:
            continue
        host, port, password = fields[1], fields[2], fields[3]
        opts = ','.join(fields[4:])
        if not (password.startswith('"') and password.endswith('"')):
            password = f'"{password}"'
        line = f'{name} = AnyTLS,{host},{port},{password}'
        if opts:
            line += ',' + opts
        nodes.append((name, line))
    return nodes


def region_of(name):
    if RU_RE.search(name):
        return 'RU 🇷🇺'
    for code, regex in REGION_RES:
        if regex.search(name):
            return code
    if EU_RE.search(name):
        return 'EU 🇪🇺'
    return None


def patch_group_line(line, new_node_names):
    """把节点名插到 url-test/select 分组里，去掉 REJECT 占位。"""
    if not new_node_names:
        return line
    head, sep, body = line.partition('=')
    if not sep:
        return line
    body = body.strip()
    parts = body.split(',')
    grp_type = parts[0]
    rest = parts[1:]
    tail_keys = ('url=', 'interval=', 'tolerance=', 'img-url=',
                 'max-timeout=', 'disable-udp=')
    tail_idx = len(rest)
    for i, p in enumerate(rest):
        if any(p.startswith(k) for k in tail_keys):
            tail_idx = i
            break
    nodes = [n for n in rest[:tail_idx] if n and n != 'REJECT']
    tail = rest[tail_idx:]
    seen = set(nodes)
    for n in new_node_names:
        if n not in seen:
            nodes.append(n)
            seen.add(n)
    return f'{head.rstrip()} = {grp_type},' + ','.join(nodes + tail)


def converter_alive():
    try:
        with socket.create_connection((CONVERTER_HOST, CONVERTER_PORT), timeout=1):
            return True
    except OSError:
        return False


def ensure_converter():
    if converter_alive():
        return
    print('[INFO] 启动 subconverter ...')
    subprocess.Popen(['subconverter\\subconverter.exe'], cwd='.',
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        time.sleep(0.5)
        if converter_alive():
            return
    raise RuntimeError('subconverter 未在预期时间内启动')


def main():
    subs = parse_subs()
    sub_url = '|'.join(u for u, _ in subs)

    ensure_converter()

    print('[INFO] 调用 subconverter 生成 Loon 配置 ...')
    resp = requests.get(CONVERTER_URL,
                        params={'target': 'loon', 'url': sub_url, 'config': 'pref.ini'},
                        timeout=60)
    if resp.status_code != 200:
        print(f'[ERR] subconverter 返回 {resp.status_code}: {resp.text[:200]}')
        raise SystemExit(1)
    content = resp.text

    # 旁路：把各订阅里 anytls 节点（subconverter 跳过的）追加进 [Proxy]，
    # 同时按地区写入对应分组
    print('[INFO] 抓取并追加 anytls 节点 ...')
    all_lines = []           # 所有 [Proxy] 段要追加的整行
    by_provider = {}         # group_prefix -> [node_name]
    by_provider_region = {}  # (group_prefix, region_code) -> [node_name]

    for url, tag in subs:
        items = fetch_anytls_nodes(url, tag)
        if not items:
            continue
        prefix = TAG_TO_GROUP.get(tag)
        print(f'  + {tag or url[:40]}: {len(items)} 节点'
              + ('' if prefix else '  (无分组前缀, 仅追加节点)'))
        for name, line in items:
            all_lines.append(line)
            if not prefix:
                continue
            by_provider.setdefault(prefix, []).append(name)
            region = region_of(name)
            if region:
                by_provider_region.setdefault((prefix, region), []).append(name)

    # 1) 注入节点行到 [Proxy] 段尾
    if all_lines:
        marker = '[Remote Proxy]'
        idx = content.find(marker)
        if idx == -1:
            proxy_idx = content.find('[Proxy]')
            idx = content.find('\n[', proxy_idx + 1)
            idx = idx + 1 if idx != -1 else len(content)
        insertion = '\n'.join(all_lines) + '\n\n'
        content = content[:idx] + insertion + content[idx:]

    # 2) 把节点名补进 [Proxy Group] 段对应分组
    out = []
    for line in content.split('\n'):
        m = re.match(r'^([^\s=]+(?:\s+\S+)?)\s*=\s*(?:url-test|select|fallback),', line)
        if m:
            grp_name = m.group(1).strip()
            # master: 名字直接等于 prefix
            if grp_name in by_provider:
                line = patch_group_line(line, by_provider[grp_name])
            else:
                # region: 形如 "<prefix><REGION 🇽🇽>"
                for (prefix, region), names in by_provider_region.items():
                    if grp_name == f'{prefix}{region}':
                        line = patch_group_line(line, names)
                        break
        out.append(line)
    content = '\n'.join(out)

    with open('loon_config.conf', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[OK] 写入 loon_config.conf, 追加 {len(all_lines)} 个 anytls 节点')


if __name__ == '__main__':
    main()
