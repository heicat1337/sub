# 获取包含链式代理的 Clash 配置

## 快速开始

### 方法一：一键脚本（推荐）

1. **确保已安装 Python 3**
   ```bash
   python3 --version
   ```

2. **运行自动脚本**
   ```bash
   # Linux/Mac
   chmod +x auto_add_chain_proxy.sh
   ./auto_add_chain_proxy.sh
   
   # Windows (使用 Git Bash 或 WSL)
   bash auto_add_chain_proxy.sh
   ```

3. **使用生成的配置文件**
   - 脚本会自动下载订阅并添加链式代理
   - 生成的配置文件：`config_with_chain.yaml`
   - 在 Clash 客户端中导入此文件即可

### 方法二：手动步骤

#### 步骤 1：获取基础配置

访问以下链接下载配置文件：

```
https://api.dler.io/sub?target=clash&url=https%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fmajor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fminor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fheicat&config=https%3A%2F%2Fraw.githubusercontent.com%2Fheicat1337%2Fsub%2Frefs%2Fheads%2Fmain%2Fpref.ini&emoji=true&list=false&sort=true&udp=true&tfo=false&scv=false&append_type=false&fdn=true&new_name=true&dual=true&dns=fake&filename=HM-ALL
```

保存为 `config.yaml`

#### 步骤 2：添加链式代理

运行 Python 脚本：

```bash
python3 add_chain_proxy.py config.yaml
```

或者手动编辑配置文件，在 `proxies:` 部分添加：

```yaml
  - name: "香港落地"
    dialer-proxy: "🇭🇰 香港节点"  # 修改为实际节点名称
    type: ss
    server: "23.175.201.164"
    port: 80
    cipher: "2022-blake3-aes-128-gcm"
    password: "UETm2mAIRiCaVJuIe1t0cA=="
    udp: true
```

#### 步骤 3：使用配置

在 Clash 客户端中导入更新后的配置文件。

## 配置链式代理节点

在运行脚本前，请先修改 `add_chain_proxy.py` 文件中的 `chain_proxies` 配置：

```python
chain_proxies = [
    {
        'name': '香港落地',
        'dialer-proxy': '🇭🇰 香港节点',  # 修改为您的实际节点名称
        'type': 'ss',
        'server': '23.175.201.164',
        'port': 80,
        'cipher': '2022-blake3-aes-128-gcm',
        'password': 'UETm2mAIRiCaVJuIe1t0cA==',
        'udp': True
    },
]
```

**重要**：`dialer-proxy` 的值必须与订阅源中的节点名称完全匹配！

## 订阅链接参数说明

- `target=clash` - 输出 Clash 格式
- `url=` - 节点源（多个用 `|` 分隔）
- `config=` - 使用您的 pref.ini 配置文件
- `dual=true` - 双订阅模式
- `dns=fake` - 使用 fake-ip DNS 模式
- `new_name=true` - 使用新字段名（proxies）

## 注意事项

1. **节点名称**：必须先获取订阅配置，查看实际的节点名称，然后修改脚本中的 `dialer-proxy` 值
2. **定期更新**：订阅会定期更新，需要重新运行脚本
3. **节点可用性**：确保基础节点和链式节点都正常工作

## 故障排除

### 问题：脚本提示节点不存在

**解决方案**：
1. 先下载订阅配置，查看实际的节点名称
2. 修改 `add_chain_proxy.py` 中的 `dialer-proxy` 值为实际节点名称
3. 重新运行脚本

### 问题：无法下载订阅

**解决方案**：
1. 检查网络连接
2. 确认订阅链接是否可访问
3. 尝试使用代理访问

### 问题：Python 脚本报错

**解决方案**：
1. 确保已安装 `pyyaml`：`pip install pyyaml`
2. 检查 Python 版本：`python3 --version`（需要 Python 3.6+）

