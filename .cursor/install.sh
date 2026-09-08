#!/usr/bin/env bash
# Cloud Agent bootstrap for the proxy config panel.
# Idempotent: safe to run repeatedly against cached/partial state.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "==> Installing Python dependencies"
pip3 install --user -r requirements.txt

echo "==> Ensuring subconverter (linux64) is present"
if [ ! -x "subconverter/subconverter" ]; then
  echo "    downloading latest subconverter_linux64..."
  curl -fL -o /tmp/subconverter.tar.gz \
    https://github.com/tindy2013/subconverter/releases/latest/download/subconverter_linux64.tar.gz
  tar -xzf /tmp/subconverter.tar.gz -C "$ROOT"
  rm -f /tmp/subconverter.tar.gz
else
  echo "    subconverter already installed"
fi

echo "==> Syncing subconverter runtime config (pref.ini)"
cp -f pref.ini subconverter/pref.ini

echo "==> Seeding local config files from examples (only if missing)"
[ -f subscriptions.txt ] || cp subscriptions.txt.example subscriptions.txt
[ -f casefarm.yaml ]     || cp casefarm.yaml.example casefarm.yaml

echo "==> Install complete"
