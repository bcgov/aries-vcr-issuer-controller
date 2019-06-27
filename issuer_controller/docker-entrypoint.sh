#!/bin/bash

export APP_NAME=${APP_NAME:-app}
export HOST_IP=${HOST_IP:-0.0.0.0}
export HOST_PORT=${HOST_PORT:-8000}

CMD="$@"
if [ -z "$CMD" ]; then
  CMD="python ${APP_NAME}.py runserver"
fi

echo "Starting server ..."
exec $CMD
