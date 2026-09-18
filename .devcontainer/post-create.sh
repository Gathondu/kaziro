#!/usr/bin/env bash
# One-time workspace provisioning. Dotfiles (zsh/nvim/skills/configs) are
# delivered by DevPod's --dotfiles flag; this script only handles what
# depends on the container itself.
set -euo pipefail

echo "==> start dockerd (docker-in-docker)"
sudo /usr/local/share/docker-init.sh

echo "==> create 1Password CLI config dir (700)"
mkdir -p "$HOME/.config/op"
chmod 700 "$HOME/.config/op"

echo "==> export OP_SERVICE_ACCOUNT_TOKEN in ~/.zshenv"
if [[ -f "$HOME/.config/op/token" ]]; then
  printf 'export OP_SERVICE_ACCOUNT_TOKEN="$(cat "$HOME/.config/op/token")"\n' > "$HOME/.zshenv"
  chmod 600 "$HOME/.zshenv"
fi

echo "==> ensure SSH agent forwarding in ~/.ssh/config"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if ! grep -q "ForwardAgent yes" "$HOME/.ssh/config" 2>/dev/null; then
  printf 'Host *\n  ForwardAgent yes\n' >> "$HOME/.ssh/config"
fi
chmod 600 "$HOME/.ssh/config"

echo "==> herdr opencode integration"
herdr integration install opencode

# Dotfiles are cloned and installed by DevPod via DOTFILES_URL + DOTFILES_SCRIPT
# in ~/.devpod/config.yaml. Just run the self-check.
if [ -f "$HOME/.dotfiles/install.sh" ]; then
  echo "==> self-check"
  ( cd "$HOME/.dotfiles" && ./install.sh --check )
else
  echo "(i) Dotfiles not installed yet — check DOTFILES_URL in devpod config" >&2
fi
