#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
链式代理自动添加脚本
用于在 Clash 配置文件中自动添加链式代理节点

使用方法：
1. 将转换后的 Clash 配置文件保存为 config.yaml
2. 修改下面的 chain_proxies 列表，配置您的链式代理节点
3. 运行脚本：python add_chain_proxy.py
4. 脚本会在原配置文件基础上添加链式代理节点
"""

import yaml
import sys
import os

# 配置您的链式代理节点
chain_proxies = [
    {
        'name': '香港落地',
        'dialer-proxy': '🇭🇰 香港节点',  # 请修改为您订阅源中实际存在的节点名称
        'type': 'ss',
        'server': '23.175.201.164',
        'port': 80,
        'cipher': '2022-blake3-aes-128-gcm',
        'password': 'UETm2mAIRiCaVJuIe1t0cA==',
        'udp': True
    },
    # 如果需要添加更多链式代理节点，可以继续添加：
    # {
    #     'name': '另一个链式节点',
    #     'dialer-proxy': '基础节点名称',
    #     'type': 'ss',
    #     'server': '服务器地址',
    #     'port': 端口,
    #     'cipher': '加密方式',
    #     'password': '密码',
    #     'udp': True
    # },
]

def add_chain_proxies(config_file='config.yaml', output_file=None):
    """
    在 Clash 配置文件中添加链式代理节点
    
    Args:
        config_file: 输入的 Clash 配置文件路径
        output_file: 输出的配置文件路径（如果为 None，则覆盖原文件）
    """
    if not os.path.exists(config_file):
        print(f"错误：配置文件 {config_file} 不存在！")
        sys.exit(1)
    
    # 读取配置文件
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"错误：无法读取配置文件 {config_file}: {e}")
        sys.exit(1)
    
    # 检查 proxies 字段
    if 'proxies' not in config:
        config['proxies'] = []
    
    # 获取现有节点名称列表
    existing_names = [proxy.get('name', '') for proxy in config['proxies']]
    
    # 添加链式代理节点
    added_count = 0
    skipped_count = 0
    
    for chain_proxy in chain_proxies:
        proxy_name = chain_proxy.get('name', '')
        dialer_proxy = chain_proxy.get('dialer-proxy', '')
        
        # 检查节点是否已存在
        if proxy_name in existing_names:
            print(f"跳过：节点 '{proxy_name}' 已存在")
            skipped_count += 1
            continue
        
        # 检查 dialer-proxy 指向的节点是否存在
        if dialer_proxy and dialer_proxy not in existing_names:
            print(f"警告：节点 '{proxy_name}' 的 dialer-proxy '{dialer_proxy}' 不存在于配置中！")
            print(f"      请确保该节点在订阅源中存在，或手动添加该节点。")
            response = input(f"      是否继续添加节点 '{proxy_name}'？(y/n): ")
            if response.lower() != 'y':
                skipped_count += 1
                continue
        
        # 添加链式代理节点
        config['proxies'].append(chain_proxy)
        existing_names.append(proxy_name)
        added_count += 1
        print(f"已添加：链式代理节点 '{proxy_name}' (dialer-proxy: '{dialer_proxy}')")
    
    # 保存配置文件
    if output_file is None:
        output_file = config_file
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"\n成功：已保存配置文件到 {output_file}")
        print(f"统计：添加 {added_count} 个节点，跳过 {skipped_count} 个节点")
    except Exception as e:
        print(f"错误：无法保存配置文件 {output_file}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # 支持命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        add_chain_proxies(input_file, output_file)
    else:
        # 默认使用 config.yaml
        add_chain_proxies()

