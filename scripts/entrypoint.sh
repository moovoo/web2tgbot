#!/bin/bash
set -e

export PYTHONUNBUFFERED=1

echo $1

if [ "$1" = "bot.bot" ] || [ "$1" = "tests" ] ; then
  while true; do
    uv run --no-dev alembic upgrade head && break || true
    sleep 1
  done
fi
uv run -m bot.startup
if [ "$1" = "tests" ] ; then
  uv run pytest -s
else
  uv run --no-dev -m "$@"
fi
