#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 config.yaml 中的 Python 字典转换为 YAML 格式的链式代理配置
用于在 all_base.tpl 中导入
"""

import yaml
import re
import sys

def parse_config_to_yaml(config_file='config.yaml', output_file='chain_proxy_from_config.yaml'):
    """解析 config.yaml 并转换为 YAML 格式"""
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取字典内容
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
    
    # 转换为 YAML 格式
    yaml_content = {
        'proxies': [result]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"已生成链式代理配置文件：{output_file}")
    return result

if __name__ == '__main__':
    parse_config_to_yaml()

