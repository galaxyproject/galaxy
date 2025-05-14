#!/bin/bash

# restart_galaxy.sh
# This script terminates any process using port 8080 (commonly Galaxy server)
# and restarts Galaxy using run.sh in the current directory.

PORT=8080

echo "🔎 Checking for processes using port $PORT..."
PID=$(lsof -ti tcp:$PORT)

if [ -n "$PID" ]; then
  echo "⚠️  Process detected on port $PORT. Terminating PID: $PID..."
  kill -9 $PID
  echo "✅ Process terminated."
else
  echo "✅ No process found on port $PORT."
fi

# Start Galaxy server
echo "🚀 Starting Galaxy server..."
if [ -x "./run.sh" ]; then
  ./run.sh
else
  echo "❌ Error: run.sh not found or not executable."
  exit 1
fi