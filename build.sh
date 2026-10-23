#!/bin/sh
# Packages the add-on as in_check_sync.ankiaddon, ready for AnkiWeb or a
# double-click install.
set -e
cd "$(dirname "$0")/minimalist_sync"
rm -f ../in_check_sync.ankiaddon
zip -q -r ../in_check_sync.ankiaddon . -x '__pycache__/*' -x '*.pyc' -x 'meta.json'
echo "built in_check_sync.ankiaddon"
