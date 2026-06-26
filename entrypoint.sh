#!/bin/sh
set -e

apt update
apt install git -y

git config --global --add safe.directory /usr/src/app

alembic upgrade head

exec python -m app
