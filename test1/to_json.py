#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 config.yaml 中的 Python 字典转换为 JSON 格式
输出紧凑格式的 JSON 字符串
"""

import json
import sys
import re

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except:
        pass

def parse_config(file_path='config.yaml'):
    """解析 config.yaml 文件中的 Python 字典"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取字典内容
    match = re.search(r'chain_proxy\s*=\s*\{', content)
    if not match:
        print("错误：找不到 chain_proxy 定义", file=sys.stderr)
        sys.exit(1)
    
    # 手动解析字典
    result = {}
    
    # 匹配所有键值对
    # 格式：'key': 'value' 或 'key': value
    pattern = r"['\"]?(\w+(?:-\w+)?)['\"]?\s*:\s*(.+?)(?=,\s*['\"]?\w|$)"
    
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
            # 尝试作为字符串
            result[key] = value.strip("'\"")
    
    return result

if __name__ == '__main__':
    try:
        config_dict = parse_config()
        
        # 转换为紧凑 JSON 格式（无空格，单行）
        json_str = json.dumps(config_dict, ensure_ascii=False, separators=(',', ':'))
        
        print(json_str)
        
    except FileNotFoundError:
        print("错误：找不到 config.yaml 文件", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)

