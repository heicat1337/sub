# config.yaml 链式代理集成说明

## 概述

现在系统支持从 `config.yaml` 文件读取链式代理配置，并自动添加到 Clash 配置文件中。链式代理节点会自动加入到 `heicat` 分组中。

## 工作流程

1. **编辑 config.yaml** - 配置链式代理节点信息
2. **运行更新脚本** - 将 config.yaml 的配置同步到 pref.ini
3. **生成订阅配置** - subconverter 会自动读取 pref.ini 并生成包含链式代理的配置
4. **自动分组** - 链式代理节点会被 `heicat` 分组匹配（根据节点名称中的地区关键词）

## 使用方法

### 步骤 1：配置链式代理

编辑 `config.yaml` 文件：

```python
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
```

### 步骤 2：更新 pref.ini

运行脚本将 config.yaml 的配置同步到 pref.ini：

```bash
python update_pref_from_config.py
```

脚本会自动：
- 读取 `config.yaml` 文件
- 解析链式代理配置
- 更新 `pref.ini` 的 `[template]` 部分

### 步骤 3：生成订阅配置

访问您的订阅链接，subconverter 会自动：
- 读取 `pref.ini` 中的链式代理配置
- 在 `all_base.tpl` 中生成链式代理节点
- 将节点添加到配置文件中

### 步骤 4：自动分组

链式代理节点 `台湾Akile` 会被 `heicat` 分组自动匹配，因为：
- `heicat` 分组使用正则：`^.*(Asia|Africa|America|Europe|Oceania|Antarctica).*$`
- 节点名称 `台湾Akile` 包含 `Asia` 关键词（台湾属于亚洲）

## 文件说明

### config.yaml
- 链式代理配置源文件
- Python 字典格式
- 易于编辑和维护

### pref.ini
- subconverter 配置文件
- `[template]` 部分包含链式代理参数
- 通过脚本从 config.yaml 自动更新

### all_base.tpl
- Clash 配置模板文件
- 自动读取 pref.ini 中的链式代理配置
- 在 `proxies:` 部分添加链式代理节点

### update_pref_from_config.py
- 自动同步脚本
- 从 config.yaml 读取配置
- 更新 pref.ini 文件

## 配置参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `name` | 链式代理节点名称 | `台湾Akile` |
| `dialer-proxy` | 基础节点名称（必须与订阅源中的节点名称完全匹配） | `AutoTW 🇨🇳` |
| `type` | 代理类型 | `ss` |
| `server` | 服务器地址 | `akilehinetnat.645781.xyz` |
| `port` | 端口 | `10490` |
| `cipher` | 加密方式 | `aes-128-gcm` |
| `password` | 密码 | `db756bc3-09ef-4550-82e0-d3c4395e8348` |
| `udp` | 是否支持 UDP | `True` |

## heicat 分组说明

`heicat` 分组配置：
```
heicat`select`!!GROUPID=2!!^.*(Asia|Africa|America|Europe|Oceania|Antarctica).*$
```

这个分组会匹配所有包含以下关键词的节点：
- Asia（亚洲）
- Africa（非洲）
- America（美洲）
- Europe（欧洲）
- Oceania（大洋洲）
- Antarctica（南极洲）

由于节点名称 `台湾Akile` 中的"台湾"属于亚洲（Asia），所以会被自动匹配到 `heicat` 分组。

## 注意事项

1. **节点名称匹配**
   - `dialer-proxy` 的值必须与订阅源中的节点名称**完全匹配**
   - 包括 emoji、空格、大小写等

2. **分组匹配**
   - 确保链式代理节点名称包含地区关键词，才能被 `heicat` 分组匹配
   - 如果节点名称不包含关键词，可以手动添加到分组中

3. **配置更新**
   - 修改 `config.yaml` 后，需要运行 `update_pref_from_config.py` 更新 `pref.ini`
   - 或者手动编辑 `pref.ini` 的 `[template]` 部分

4. **启用配置**
   - 确保 `pref.ini` 中 `chain_proxy.enable=true`
   - 如果设置为 `false` 或不设置，链式代理节点不会被添加

## 自动化流程

如果您希望自动化这个过程，可以：

1. **使用 Git Hook**：在提交 config.yaml 时自动运行更新脚本
2. **使用 CI/CD**：在 GitHub Actions 中自动同步配置
3. **定期任务**：设置定时任务自动更新配置

## 故障排除

### 问题：链式代理节点没有出现

**解决方案**：
1. 检查 `pref.ini` 中 `chain_proxy.enable=true`
2. 运行 `python update_pref_from_config.py` 更新配置
3. 确认所有必需参数都已配置

### 问题：节点没有被 heicat 分组匹配

**解决方案**：
1. 检查节点名称是否包含地区关键词（Asia、Europe 等）
2. 如果节点名称不包含关键词，可以手动在 `group.txt` 中添加节点名称

### 问题：dialer-proxy 节点不存在

**解决方案**：
1. 先获取一次订阅配置，查看实际的节点名称
2. 更新 `config.yaml` 中的 `dialer-proxy` 值
3. 重新运行 `update_pref_from_config.py`

