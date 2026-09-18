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
LINE='export OP_SERVICE_ACCOUNT_TOKEN="$(cat "$HOME/.config/op/token")"'
if [ ! -f "$HOME/.zshenv" ]; then
  printf '%s\n' "$LINE" > "$HOME/.zshenv"
  chmod 600 "$HOME/.zshenv"
elif grep -qF "$LINE" "$HOME/.zshenv" 2>/dev/null; then
  echo "    OP_SERVICE_ACCOUNT_TOKEN already set in ~/.zshenv — skipping"
else
  printf '%s\n' "$LINE" >> "$HOME/.zshenv"
  chmod 600 "$HOME/.zshenv"
fi

echo "==> remove DevPod's gpg.ssh.program from ~/.gitconfig (dotfiles version wins)"
if [ -f "$HOME/.gitconfig" ] && grep -q 'devpod-ssh-signature' "$HOME/.gitconfig" 2>/dev/null; then
  git config --global --unset gpg.ssh.program 2>/dev/null || true
  git config --global --remove-section gpg.ssh 2>/dev/null || true
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

echo "==> ensure dockerd auto-starts on every shell login"
# postStartCommand only fires on container creation, not host restarts.
# The dotfiles install may overwrite .zshrc, so inject this line last.
LINE='sudo /usr/local/share/docker-init.sh >/dev/null 2>&1 &'
if ! grep -qF "$LINE" "$HOME/.zshrc" 2>/dev/null; then
  printf '\n# Start docker-in-docker (idempotent — no-ops if already running)\n%s\n' "$LINE" >> "$HOME/.zshrc"
fi
