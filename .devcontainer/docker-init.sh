#!/bin/sh
# Idempotent dockerd starter for docker-in-docker. Run as root via sudo
# (postStartCommand). No-op when the daemon is already up.
set -e

if docker info >/dev/null 2>&1; then
    echo "dockerd already running"
    exit 0
fi

# Clear stale pid files from unclean container restarts.
find /run /var/run -iname 'docker*.pid' -delete 2>/dev/null || true
find /run /var/run -iname 'container*.pid' -delete 2>/dev/null || true

nohup dockerd > /tmp/dockerd.log 2>&1 &

i=1
while [ "$i" -le 30 ]; do
    if docker info >/dev/null 2>&1; then
        echo "dockerd up"
        exit 0
    fi
    sleep 1
    i=$((i + 1))
done

echo "dockerd failed to start; see /tmp/dockerd.log" >&2
exit 1
