# JSON 转换脚本使用说明

## 功能

将 `config.yaml` 中的 Python 字典格式转换为紧凑的 JSON 格式。

## 使用方法

### 基本使用

```bash
python to_json.py
```

### 输出示例

输入（config.yaml）：
```python
chain_proxy = {
    'name': '台湾Akile',
    'dialer-proxy': 'AutoTW 🇨🇳',
    'type': 'ss',
    'server': 'akilehinetnat.645781.xyz',
    'port': 10490,
    'cipher': 'aes-128-gcm',
    'password': 'db756bc3-09ef-4550-82e0-d3c4395e8348',
    'udp': True
}
```

输出：
```json
{"name":"台湾Akile","dialer-proxy":"AutoTW 🇨🇳","type":"ss","server":"akilehinetnat.645781.xyz","port":10490,"cipher":"aes-128-gcm","password":"db756bc3-09ef-4550-82e0-d3c4395e8348","udp":true}
```

## 脚本说明

### to_json.py（推荐）

- 简单、快速
- 输出紧凑格式的 JSON（单行，无空格）
- 自动处理编码问题（Windows 兼容）

### convert_to_json_simple.py

- 功能更完整
- 支持保存到文件
- 支持美化格式输出

### convert_to_json.py

- 完整版本
- 支持多种输出格式

## 修改配置

如果需要修改服务器地址、端口等信息，直接编辑 `config.yaml` 文件，然后重新运行脚本即可。

例如，如果要更新服务器地址和端口：

```python
chain_proxy = {
    'name': '台湾Akile',
    'dialer-proxy': 'AutoTW 🇨🇳',
    'type': 'ss',
    'server': 'iepl.ac.hk.4.dlers.cloud',  # 修改服务器地址
    'port': 30899,  # 修改端口
    'cipher': 'aes-128-gcm',
    'password': 'db756bc3-09ef-4550-82e0-d3c4395e8348',
    'udp': True
}
```

运行脚本后输出：
```json
{"name":"台湾Akile","dialer-proxy":"AutoTW 🇨🇳","type":"ss","server":"iepl.ac.hk.4.dlers.cloud","port":30899,"cipher":"aes-128-gcm","password":"db756bc3-09ef-4550-82e0-d3c4395e8348","udp":true}
```

## 注意事项

1. 确保 `config.yaml` 文件存在且格式正确
2. 脚本会自动忽略注释（`#` 后面的内容）
3. 输出格式为紧凑 JSON（无空格，适合复制粘贴）
4. Windows 系统会自动处理编码问题

