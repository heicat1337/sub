#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 config.yaml 中的 Python 字典格式转换为 JSON 格式

使用方法：
1. 确保 config.yaml 文件存在
2. 运行：python convert_to_json.py
3. 脚本会输出 JSON 格式的配置
"""

import json
import re
import sys
import os

def parse_python_dict(file_path):
    """
    解析 config.yaml 中的 Python 字典格式
    
    Args:
        file_path: 配置文件路径
    
    Returns:
        dict: 解析后的字典
    """
    if not os.path.exists(file_path):
        print(f"错误：文件 {file_path} 不存在！")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取字典内容（从 chain_proxy = { 到 }）
    match = re.search(r'chain_proxy\s*=\s*\{([^}]+)\}', content, re.DOTALL)
    if not match:
        print("错误：无法找到 chain_proxy 字典定义")
        sys.exit(1)
    
    dict_content = match.group(1)
    
    # 解析字典内容
    result = {}
    
    # 匹配键值对
    # 处理 'key': 'value' 或 'key': value 格式
    pattern = r"['\"]?(\w+(?:-\w+)?)['\"]?\s*:\s*(.+?)(?=,\s*['\"]?\w|$)"
    
    for line in dict_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
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
        value = parts[1].strip()
        
        # 处理值
        if value.startswith("'") and value.endswith("'"):
            # 字符串值
            result[key] = value.strip("'")
        elif value.startswith('"') and value.endswith('"'):
            # 字符串值
            result[key] = value.strip('"')
        elif value.lower() == 'true':
            # 布尔值 True
            result[key] = True
        elif value.lower() == 'false':
            # 布尔值 False
            result[key] = False
        elif value.isdigit():
            # 整数
            result[key] = int(value)
        else:
            # 尝试作为字符串处理
            result[key] = value.strip("'\"")
    
    return result

def convert_to_json(config_file='config.yaml', output_format='compact'):
    """
    将配置文件转换为 JSON 格式
    
    Args:
        config_file: 输入文件路径
        output_format: 输出格式 ('compact' 紧凑格式, 'pretty' 美化格式)
    """
    # 解析 Python 字典
    config_dict = parse_python_dict(config_file)
    
    # 转换为 JSON
    if output_format == 'compact':
        # 紧凑格式（单行，无空格）
        json_str = json.dumps(config_dict, ensure_ascii=False, separators=(',', ':'))
    else:
        # 美化格式（多行，缩进）
        json_str = json.dumps(config_dict, ensure_ascii=False, indent=2)
    
    return json_str, config_dict

if __name__ == '__main__':
    # 支持命令行参数
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'compact'
    
    try:
        json_str, config_dict = convert_to_json(config_file, output_format)
        
        # 输出 JSON
        print(json_str)
        
        # 可选：保存到文件
        if len(sys.argv) > 3:
            output_file = sys.argv[3]
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"\n已保存到文件：{output_file}", file=sys.stderr)
        
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)

