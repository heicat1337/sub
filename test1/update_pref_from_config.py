#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 config.yaml 读取链式代理配置，并更新到 pref.ini 的 [template] 部分
这样 all_base.tpl 就可以通过模板变量读取配置了
"""

import re
import sys

def parse_config_yaml(config_file='config.yaml'):
    """解析 config.yaml 文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = {}
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('{') or line.startswith('}'):
            continue
        
        # 移除行尾注释
        if '#' in line:
            line = line[:line.index('#')].rstrip()
        
        # 移除末尾的逗号
        line = line.rstrip(',').strip()
        
        if ':' not in line:
            continue
        
        # 分割键值
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
        
        key = parts[0].strip().strip("'\"")
        value = parts[1].strip().rstrip(',').strip()
        
        # 处理值
        if value.startswith("'") and value.endswith("'"):
            result[key] = value.strip("'")
        elif value.startswith('"') and value.endswith('"'):
            result[key] = value.strip('"')
        elif value == 'True':
            result[key] = True
        elif value == 'False':
            result[key] = False
        elif value.isdigit():
            result[key] = int(value)
        else:
            result[key] = value.strip("'\"")
    
    return result

def update_pref_ini(config_dict, pref_file='pref.ini'):
    """更新 pref.ini 文件的 [template] 部分"""
    with open(pref_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 [template] 部分
    template_section = re.search(r'(\[template\].*?)(?=\n\[|\Z)', content, re.DOTALL)
    
    if not template_section:
        # 如果没有 [template] 部分，在文件末尾添加
        template_content = """
[template]
;链式代理配置（从 config.yaml 自动更新）
chain_proxy.enable=true
chain_proxy.name={name}
chain_proxy.dialer_proxy={dialer_proxy}
chain_proxy.type={type}
chain_proxy.server={server}
chain_proxy.port={port}
chain_proxy.cipher={cipher}
chain_proxy.password={password}
chain_proxy.udp={udp}
""".format(
            name=config_dict.get('name', '台湾Akile'),
            dialer_proxy=config_dict.get('dialer-proxy', 'AutoTW 🇨🇳'),
            type=config_dict.get('type', 'ss'),
            server=config_dict.get('server', 'akilehinetnat.645781.xyz'),
            port=config_dict.get('port', 10490),
            cipher=config_dict.get('cipher', 'aes-128-gcm'),
            password=config_dict.get('password', 'db756bc3-09ef-4550-82e0-d3c4395e8348'),
            udp=str(config_dict.get('udp', True)).lower()
        )
        content += template_content
    else:
        # 更新现有的 [template] 部分
        template_start = template_section.start()
        template_end = template_section.end()
        template_text = template_section.group(1)
        
        # 更新或添加链式代理配置
        chain_proxy_config = f""";链式代理配置（从 config.yaml 自动更新）
chain_proxy.enable=true
chain_proxy.name={config_dict.get('name', '台湾Akile')}
chain_proxy.dialer_proxy={config_dict.get('dialer-proxy', 'AutoTW 🇨🇳')}
chain_proxy.type={config_dict.get('type', 'ss')}
chain_proxy.server={config_dict.get('server', 'akilehinetnat.645781.xyz')}
chain_proxy.port={config_dict.get('port', 10490)}
chain_proxy.cipher={config_dict.get('cipher', 'aes-128-gcm')}
chain_proxy.password={config_dict.get('password', 'db756bc3-09ef-4550-82e0-d3c4395e8348')}
chain_proxy.udp={str(config_dict.get('udp', True)).lower()}
"""
        
        # 移除旧的链式代理配置（如果存在）
        template_text = re.sub(r';链式代理配置.*?\n(?:chain_proxy\..*?\n)*', '', template_text, flags=re.DOTALL)
        
        # 添加新的配置
        template_text += chain_proxy_config
        
        # 替换原内容
        content = content[:template_start] + template_text + content[template_end:]
    
    # 保存文件
    with open(pref_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已更新 {pref_file} 文件")

if __name__ == '__main__':
    try:
        config_dict = parse_config_yaml()
        update_pref_ini(config_dict)
        print("配置已从 config.yaml 更新到 pref.ini")
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)

