终极魔改版

## 链式代理配置说明

### 什么是链式代理？

链式代理（Chain Proxy）允许您将流量通过多个代理节点进行转发。在 Clash 中，使用 `dialer-proxy` 字段来实现链式代理。

### 配置方法（推荐使用脚本）

由于 subconverter 的 `pref.ini` 不支持直接添加带 `dialer-proxy` 的链式代理节点，推荐使用以下方法：

#### 方法一：使用自动脚本（推荐）

1. **修改脚本配置**
   - 打开 `add_chain_proxy.py` 文件
   - 修改 `chain_proxies` 列表，配置您的链式代理节点
   - 确保 `dialer-proxy` 的值与订阅源中的节点名称完全匹配

2. **运行脚本**
   ```bash
   # 将转换后的配置文件保存为 config.yaml，然后运行：
   python add_chain_proxy.py config.yaml
   
   # 或者指定输出文件：
   python add_chain_proxy.py config.yaml output.yaml
   ```

3. **脚本会自动**
   - 检查节点是否已存在
   - 验证 dialer-proxy 指向的节点是否存在
   - 添加链式代理节点到配置文件

#### 方法二：手动编辑配置文件

1. **获取转换后的 Clash 配置文件**
   - 通过 subconverter 生成 Clash 配置
   - 打开生成的配置文件（通常是 `.yaml` 或 `.yml` 文件）

2. **找到 `proxies:` 部分并添加链式代理节点**

参考 `chain_proxy_example.yaml` 文件查看完整的配置示例。

基本格式：
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
```

### 注意事项

1. `dialer-proxy` 字段的值必须是已存在的代理节点名称（完全匹配，包括 emoji 和空格）
2. 基础节点必须在链式代理节点之前定义
3. 链式代理会增加延迟，请根据实际需求使用
4. 确保基础节点和链式节点都正常工作

### 工作原理

流量路径：客户端 → 基础节点（dialer-proxy） → 链式节点 → 目标服务器

例如，使用 "香港落地" 节点时：
- 流量首先通过 "🇭🇰 香港节点"
- 然后通过 "香港落地" 节点
- 最后到达目标服务器

### pref.ini 配置说明

在 `pref.ini` 文件中，已添加了链式代理的配置选项（默认注释）：
```ini
;Options for adding custom proxy nodes (including chain proxies)
;add_proxy=!!import:https://raw.githubusercontent.com/heicat1337/sub/refs/heads/main/chain_proxies.yaml
```

**注意**：由于 subconverter 的限制，`add_proxy` 参数可能无法直接导入带 `dialer-proxy` 的链式代理节点。建议使用脚本方法或手动编辑配置文件。