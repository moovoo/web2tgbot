#!/bin/bash
PYTHONUNBUFFERED=1

echo $1

if [ "$1" = "bot.bot" ]; then
  while true; do
    alembic upgrade head && break || true
    sleep 1
  done
fi

python -m bot.startup
python -m $1
