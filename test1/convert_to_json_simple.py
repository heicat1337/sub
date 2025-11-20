#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版：直接将 config.yaml 中的 Python 字典转换为 JSON

使用方法：
python convert_to_json_simple.py
"""

import json
import ast
import sys

def convert_config_to_json(config_file='config.yaml'):
    """
    读取 config.yaml，提取 Python 字典并转换为 JSON
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用 ast.literal_eval 安全地解析 Python 字典
        # 先提取字典部分
        if 'chain_proxy = {' in content:
            # 找到字典开始和结束位置
            start = content.find('chain_proxy = {')
            if start == -1:
                print("错误：找不到 chain_proxy 定义")
                sys.exit(1)
            
            # 找到匹配的右括号
            brace_count = 0
            i = start + len('chain_proxy = {')
            dict_start = i
            
            for i in range(dict_start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == -1:
                        dict_end = i
                        break
            else:
                print("错误：找不到匹配的右括号")
                sys.exit(1)
            
            dict_str = content[dict_start-1:dict_end+1]  # 包含 {}
            
            # 移除注释
            lines = []
            for line in dict_str.split('\n'):
                if '#' in line:
                    line = line[:line.index('#')]
                lines.append(line)
            dict_str = '\n'.join(lines)
            
            # 使用 ast.literal_eval 解析
            try:
                config_dict = ast.literal_eval(dict_str)
            except:
                # 如果 ast 解析失败，尝试手动解析
                config_dict = {}
                # 简单的键值对解析
                for line in dict_str.split('\n'):
                    line = line.strip().rstrip(',')
                    if ':' in line and not line.strip().startswith('{') and not line.strip().startswith('}'):
                        key, value = line.split(':', 1)
                        key = key.strip().strip("'\"")
                        value = value.strip().rstrip(',').strip()
                        
                        # 处理值
                        if value.startswith("'") and value.endswith("'"):
                            config_dict[key] = value.strip("'")
                        elif value.startswith('"') and value.endswith('"'):
                            config_dict[key] = value.strip('"')
                        elif value == 'True':
                            config_dict[key] = True
                        elif value == 'False':
                            config_dict[key] = False
                        elif value.isdigit():
                            config_dict[key] = int(value)
                        else:
                            config_dict[key] = value.strip("'\"")
        else:
            print("错误：找不到 chain_proxy 定义")
            sys.exit(1)
        
        # 转换为紧凑 JSON 格式
        json_str = json.dumps(config_dict, ensure_ascii=False, separators=(',', ':'))
        
        return json_str, config_dict
        
    except FileNotFoundError:
        print(f"错误：文件 {config_file} 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)

if __name__ == '__main__':
    # 设置标准输出编码为 UTF-8（Windows 兼容）
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    json_str, config_dict = convert_config_to_json()
    print(json_str)
    
    # 如果提供了输出文件参数，保存到文件
    if len(sys.argv) > 1 and sys.argv[1] != 'config.yaml':
        output_file = sys.argv[1]
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"\n已保存到：{output_file}", file=sys.stderr)

