#!/bin/bash

export APP_NAME=${APP_NAME:-app}
export HOST_IP=${HOST_IP:-0.0.0.0}
export HOST_PORT=${WEBHOOK_PORT:-5000}

CMD="$@"
if [ -z "$CMD" ]; then
  CMD="python ${APP_NAME}.py runserver --host=0.0.0.0 --threaded"
fi

echo "Starting server ..."
exec $CMD
