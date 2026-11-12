#!/usr/bin/env bash
# Render上でのビルド処理
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
