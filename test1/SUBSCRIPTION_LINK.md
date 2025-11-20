# 订阅链接使用说明

## 基础订阅链接（不含链式代理）

您的基础订阅链接：

```
https://api.dler.io/sub?target=clash&url=https%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fmajor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fminor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fheicat&config=https%3A%2F%2Fraw.githubusercontent.com%2Fheicat1337%2Fsub%2Frefs%2Fheads%2Fmain%2Fpref.ini&emoji=true&list=false&sort=true&udp=true&tfo=false&scv=false&append_type=false&fdn=true&new_name=true&dual=true&dns=fake&filename=HM-ALL
```

## 添加链式代理的方法

由于 subconverter 的限制，无法直接在订阅链接中添加带 `dialer-proxy` 的链式代理节点。推荐使用以下方法：

### 方法一：使用自动脚本（推荐）

1. **下载转换后的配置文件**
   - 访问上面的订阅链接
   - 保存生成的配置文件（例如：`config.yaml`）

2. **修改并运行脚本**
   ```bash
   # 修改 add_chain_proxy.py 中的 chain_proxies 配置
   # 然后运行：
   python add_chain_proxy.py config.yaml
   ```

3. **使用生成的配置文件**
   - 脚本会自动添加链式代理节点
   - 使用生成的配置文件即可

### 方法二：手动添加（快速方法）

1. **下载配置文件**
   - 访问订阅链接，下载生成的 Clash 配置文件

2. **找到节点名称**
   - 打开配置文件，找到 `proxies:` 部分
   - 找到您要作为基础节点的节点名称（例如：`🇭🇰 香港节点`）

3. **添加链式代理节点**
   - 在 `proxies:` 列表末尾添加以下内容：

```yaml
  - name: "香港落地"
    dialer-proxy: "🇭🇰 香港节点"  # 修改为您实际的基础节点名称
    type: ss
    server: "23.175.201.164"
    port: 80
    cipher: "2022-blake3-aes-128-gcm"
    password: "UETm2mAIRiCaVJuIe1t0cA=="
    udp: true
```

4. **保存并使用**
   - 保存配置文件
   - 在 Clash 客户端中导入更新后的配置

## 链接参数说明

- `target=clash` - 目标格式为 Clash
- `url=` - 节点源（多个用 `|` 分隔）
- `config=` - 配置文件（pref.ini）
- `dual=true` - 启用双订阅模式
- `dns=fake` - DNS 模式
- `new_name=true` - 使用新字段名（proxies 而不是 Proxy）

## 注意事项

1. **节点名称匹配**：`dialer-proxy` 的值必须与订阅源中的节点名称**完全匹配**（包括 emoji、空格等）
2. **节点顺序**：基础节点必须在链式节点之前定义（通常订阅源中的节点已经在前面）
3. **定期更新**：订阅链接会定期更新，需要重新添加链式代理节点

## 自动化方案

如果您希望自动化这个过程，可以考虑：

1. **使用 GitHub Actions**：自动下载配置、添加链式代理、上传到仓库
2. **使用本地脚本**：定期运行脚本更新配置文件
3. **使用 Clash 客户端脚本**：在客户端中自动添加链式代理节点

