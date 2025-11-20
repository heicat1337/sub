# 链式代理配置指南

## 概述

链式代理（Chain Proxy）允许您将流量通过多个代理节点进行转发。在 Clash 中，使用 `dialer-proxy` 字段来实现链式代理。

## 工作原理

```
客户端 → 基础节点（dialer-proxy） → 链式节点 → 目标服务器
```

当您使用链式代理节点时，流量会先通过 `dialer-proxy` 指定的基础节点，然后再通过链式节点本身。

## 在 subconverter 项目中的配置方法

本项目使用 subconverter 进行订阅转换，通过 `pref.ini` 文件配置。由于 subconverter 的限制，无法直接在 `pref.ini` 中添加带 `dialer-proxy` 的链式代理节点。

**推荐方法**：使用 `add_chain_proxy.py` 脚本在转换后自动添加链式代理节点。

## 配置步骤

### 方法一：使用自动脚本（推荐，适用于 subconverter）

1. **修改脚本配置**
   - 打开 `add_chain_proxy.py` 文件
   - 找到 `chain_proxies` 列表
   - 修改配置，设置您的链式代理节点信息
   - **重要**：确保 `dialer-proxy` 的值与订阅源中的节点名称完全匹配

2. **运行脚本**
   ```bash
   # 将 subconverter 转换后的配置文件保存为 config.yaml
   # 然后运行脚本：
   python add_chain_proxy.py config.yaml
   
   # 或者指定输出文件（不覆盖原文件）：
   python add_chain_proxy.py config.yaml output.yaml
   ```

3. **脚本功能**
   - 自动检查节点是否已存在（避免重复添加）
   - 验证 dialer-proxy 指向的节点是否存在
   - 自动添加链式代理节点到配置文件
   - 显示添加结果和统计信息

### 方法二：手动编辑配置文件

1. **获取转换后的 Clash 配置文件**
   - 通过 subconverter 生成 Clash 配置
   - 打开生成的配置文件（通常是 `.yaml` 或 `.yml` 文件）

2. **找到 `proxies:` 部分**
   - 在配置文件中找到 `proxies:` 字段
   - 确认基础节点（您要作为上游的节点）的名称

3. **添加链式代理节点**
   - 在 `proxies:` 列表中添加新的链式代理节点
   - 确保基础节点在链式节点之前定义

4. **示例配置**

```yaml
proxies:
  # 基础节点（必须已存在，从订阅源获取）
  - name: "🇭🇰 香港节点"
    type: ss
    server: "example.com"
    port: 443
    cipher: "aes-256-gcm"
    password: "password"
    udp: true

  # 链式代理节点（手动添加）
  - name: "香港落地"
    dialer-proxy: "🇭🇰 香港节点"  # 指向基础节点
    type: ss
    server: "23.175.201.164"
    port: 80
    cipher: "2022-blake3-aes-128-gcm"
    password: "UETm2mAIRiCaVJuIe1t0cA=="
    udp: true

  - name: "直连"
    type: direct
```

### 方法二：使用脚本自动添加

如果您需要批量添加链式代理，可以使用脚本工具。以下是 Python 示例：

```python
import yaml

# 读取配置文件
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 定义链式代理节点
chain_proxy = {
    'name': '台湾Akile',
    'dialer-proxy': 'AutoTW 🇨🇳',  # 确保这个节点存在
    'type': 'ss',
    'server': 'akilehinetnat.645781.xyz',
    'port': 10490,
    'cipher': 'aes-128-gcm',
    'password': 'db756bc3-09ef-4550-82e0-d3c4395e8348',
    'udp': True
}

# 添加到代理列表
if 'proxies' in config:
    config['proxies'].append(chain_proxy)
else:
    config['proxies'] = [chain_proxy]

# 保存配置文件
with open('config.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
```

## 配置参数说明

### 必需字段

- `name`: 代理节点名称（唯一标识）
- `dialer-proxy`: 基础代理节点名称（必须与已存在的节点名称完全匹配）
- `type`: 代理类型（ss, vmess, trojan, http, socks5 等）
- `server`: 服务器地址
- `port`: 服务器端口

### 可选字段（根据代理类型而定）

- `cipher`: 加密方式（SS 代理需要）
- `password`: 密码（SS 代理需要）
- `udp`: 是否支持 UDP（布尔值）
- 其他代理类型特定的字段

## 注意事项

1. **节点名称匹配**
   - `dialer-proxy` 的值必须与已存在的代理节点名称**完全匹配**（包括空格、特殊字符、emoji）
   - 建议复制粘贴节点名称，避免手动输入错误

2. **节点顺序**
   - 基础节点必须在链式代理节点之前定义
   - 如果基础节点在链式节点之后，会导致配置错误

3. **性能影响**
   - 链式代理会增加延迟（两个节点的延迟相加）
   - 建议仅在必要时使用

4. **节点可用性**
   - 确保基础节点和链式节点都正常工作
   - 如果基础节点不可用，链式节点也无法使用

5. **代理类型兼容性**
   - 不是所有代理类型都支持链式代理
   - 建议使用 SS、VMess、Trojan 等常见类型

## 常见问题

### Q: 如何确认基础节点名称？

A: 在配置文件的 `proxies:` 部分查找节点，复制完整的 `name` 字段值。

### Q: 链式代理失败怎么办？

A: 检查以下几点：
1. `dialer-proxy` 的值是否与基础节点名称完全匹配
2. 基础节点是否在链式节点之前定义
3. 基础节点和链式节点是否都正常工作
4. 查看 Clash 日志获取详细错误信息

### Q: 可以链式多个节点吗？

A: Clash 支持链式多个节点，但需要逐层配置：
- 节点 A（基础）
- 节点 B（dialer-proxy: 节点 A）
- 节点 C（dialer-proxy: 节点 B）

### Q: 链式代理会影响速度吗？

A: 是的，链式代理会增加延迟，因为流量需要经过多个节点。延迟 ≈ 基础节点延迟 + 链式节点延迟。

## 参考示例

完整示例请参考 `chain_proxy_example.yaml` 文件。

