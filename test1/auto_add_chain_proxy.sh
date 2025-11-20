#!/bin/bash
# 自动获取订阅并添加链式代理的脚本
# 使用方法：./auto_add_chain_proxy.sh

# 订阅链接
SUBSCRIPTION_URL="https://api.dler.io/sub?target=clash&url=https%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fmajor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fminor%7Chttps%3A%2F%2Fgist.githubusercontent.com%2Fheicat1337%2Fed424c22310d9668ae1286d9801b82b9%2Fraw%2Fheicat&config=https%3A%2F%2Fraw.githubusercontent.com%2Fheicat1337%2Fsub%2Frefs%2Fheads%2Fmain%2Fpref.ini&emoji=true&list=false&sort=true&udp=true&tfo=false&scv=false&append_type=false&fdn=true&new_name=true&dual=true&dns=fake&filename=HM-ALL"

# 临时配置文件
TEMP_CONFIG="temp_config.yaml"
OUTPUT_CONFIG="config_with_chain.yaml"

echo "正在下载订阅配置..."
curl -s "$SUBSCRIPTION_URL" -o "$TEMP_CONFIG"

if [ $? -ne 0 ]; then
    echo "错误：无法下载订阅配置"
    exit 1
fi

echo "订阅配置已下载到 $TEMP_CONFIG"
echo "正在添加链式代理节点..."

# 使用 Python 脚本添加链式代理
python3 add_chain_proxy.py "$TEMP_CONFIG" "$OUTPUT_CONFIG"

if [ $? -eq 0 ]; then
    echo "成功！配置文件已保存到 $OUTPUT_CONFIG"
    echo "您可以在 Clash 客户端中导入此配置文件"
else
    echo "错误：添加链式代理失败"
    exit 1
fi

# 清理临时文件
# rm "$TEMP_CONFIG"

