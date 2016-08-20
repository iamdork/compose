#!/usr/bin/env bash

echo "Checking for listeners on port 80 and 53"

for port in 80 53; do
  for i in $(sudo lsof -i :$port | awk '{print $2}' | tail -n +2 | xargs); do
    echo ""
    sleep 1
    echo "Killing PID $i cause it's listening on port 53"
    echo "PID $i info:"
    sudo ps -p "$i" -o user -o command
    sudo kill "$i"
    echo ""
  done
done
