#!/usr/bin/env bash
# One-time workspace provisioning. Dotfiles (zsh/nvim/skills/configs) are
# delivered by DevPod's --dotfiles flag; this script only handles what
# depends on the container itself.
set -euo pipefail

echo "==> start dockerd (docker-in-docker)"
sudo sh /workspaces/kaziro/.devcontainer/docker-init.sh

echo "==> create 1Password CLI config dir (700)"
mkdir -p "$HOME/.config/op"
chmod 700 "$HOME/.config/op"

echo "==> herdr opencode integration"
herdr integration install opencode

if [ -f "$HOME/.dotfiles/install.sh" ] || [ -f "$HOME/dotfiles/install.sh" ]; then
  echo "==> self-check"
  ( cd "$HOME/.dotfiles" 2>/dev/null || cd "$HOME/dotfiles"; ./install.sh --check )
else
  echo "(i) Dotfiles not installed yet — start the workspace with:" >&2
  echo "    devpod up kaziro --dotfiles https://github.com/Gathondu/dotfiles.git" >&2
fi
