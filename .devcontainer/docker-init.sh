#!/bin/sh
# Idempotent dockerd starter for docker-in-docker. Run as root via sudo
# (postStartCommand). No-op when the daemon is already up.
set -e

# Always (re)write daemon.json: DevPod bakes in a copy of the host's config
# whose bip/dns point at 172.17.0.1 — the outer docker0 gateway that this
# container itself lives on. That duplicate address makes the workspace
# ignore the host's ARP requests (periodic total-network blackholes) and
# gives nested containers a dead DNS server. Keep the inner bridge and all
# compose networks out of the host's 172.17.0.0/16.
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" },
  "bip": "172.24.0.1/16",
  "default-address-pools": [{ "base": "172.25.0.0/16", "size": 24 }],
  "dns": ["1.1.1.1", "8.8.8.8"]
}
EOF

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
