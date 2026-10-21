#!/bin/sh
# Packages the add-on as minimalist_sync.ankiaddon, ready for AnkiWeb or a
# double-click install.
set -e
cd "$(dirname "$0")/minimalist_sync"
rm -f ../minimalist_sync.ankiaddon
zip -q -r ../minimalist_sync.ankiaddon . -x '__pycache__/*' -x '*.pyc' -x 'meta.json'
echo "built minimalist_sync.ankiaddon"
