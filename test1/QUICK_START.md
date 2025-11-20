# 快速开始：获取包含链式代理的 Clash 配置

## 🚀 最简单的方法（一键脚本）

### Windows 用户

1. **下载配置文件**
   - 访问：https://api.dler.io/sub?target=clash&url=https%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fmajor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fminor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fheicat&config=https%3A%2F%2Fraw.githubusercontent.com%2Fheicat1337%2Fsub%2Frefs%2Fheads%2Fmain%2Fpref.ini&emoji=true&list=false&sort=true&udp=true&tfo=false&scv=false&append_type=false&fdn=true&new_name=true&dual=true&dns=fake&filename=HM-ALL
   - 右键 → 另存为 → `config.yaml`

2. **修改脚本配置**
   - 打开 `add_chain_proxy.py`
   - 找到第 22 行，修改 `dialer-proxy` 的值为您订阅中的实际节点名称
   - 保存文件

3. **运行脚本**
   ```powershell
   python add_chain_proxy.py config.yaml
   ```

4. **使用配置**
   - 脚本会在原文件基础上添加链式代理
   - 在 Clash 客户端中导入 `config.yaml` 即可

### Linux/Mac 用户

1. **运行自动脚本**
   ```bash
   chmod +x auto_add_chain_proxy.sh
   ./auto_add_chain_proxy.sh
   ```

2. **使用生成的配置**
   - 配置文件：`config_with_chain.yaml`
   - 在 Clash 客户端中导入即可

## 📝 详细步骤

### 步骤 1：获取基础节点名称

1. 访问订阅链接，下载配置文件
2. 打开配置文件，找到 `proxies:` 部分
3. 查看节点名称，例如：`🇭🇰 香港节点`、`🇯🇵 日本节点` 等
4. **复制完整的节点名称**（包括 emoji 和空格）

### 步骤 2：配置链式代理

打开 `add_chain_proxy.py`，修改以下部分：

```python
chain_proxies = [
    {
        'name': '香港落地',  # 链式代理节点名称（可自定义）
        'dialer-proxy': '🇭🇰 香港节点',  # ⚠️ 修改为您从步骤1复制的实际节点名称
        'type': 'ss',
        'server': '23.175.201.164',  # 您的链式代理服务器地址
        'port': 80,  # 端口
        'cipher': '2022-blake3-aes-128-gcm',  # 加密方式
        'password': 'UETm2mAIRiCaVJuIe1t0cA==',  # 密码
        'udp': True
    },
]
```

### 步骤 3：运行脚本

```bash
# 方法1：直接运行（会覆盖原文件）
python add_chain_proxy.py config.yaml

# 方法2：生成新文件（推荐）
python add_chain_proxy.py config.yaml config_with_chain.yaml
```

### 步骤 4：导入 Clash

在 Clash 客户端中导入更新后的配置文件即可使用链式代理。

## ⚠️ 重要提示

1. **节点名称必须完全匹配**
   - `dialer-proxy` 的值必须与订阅中的节点名称**完全一致**
   - 包括 emoji、空格、大小写等

2. **先获取节点名称**
   - 必须先下载订阅配置，查看实际的节点名称
   - 然后修改脚本中的 `dialer-proxy` 值

3. **定期更新**
   - 订阅会定期更新，需要重新运行脚本添加链式代理

## 🔗 您的订阅链接

```
https://api.dler.io/sub?target=clash&url=https%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fmajor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fminor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fheicat&config=https%3A%2F%2Fraw.githubusercontent.com%2Fheicat1337%2Fsub%2Frefs%2Fheads%2Fmain%2Fpref.ini&emoji=true&list=false&sort=true&udp=true&tfo=false&scv=false&append_type=false&fdn=true&new_name=true&dual=true&dns=fake&filename=HM-ALL
```

## 📚 更多信息

- 详细使用指南：查看 `GET_SUBSCRIPTION.md`
- 订阅链接说明：查看 `SUBSCRIPTION_LINK.md`
- 链式代理原理：查看 `CHAIN_PROXY_GUIDE.md`

