#!/bin/bash
export PYTHONUNBUFFERED=1

echo $1

if [ "$1" = "bot.bot" ] || [ "$1" = "tests" ] ; then
  while true; do
    alembic upgrade head && break || true
    sleep 1
  done
fi
python -m bot.startup
if [ "$1" = "tests" ] ; then
  python -m pytest -s
else
  python -m "$@"
fi
