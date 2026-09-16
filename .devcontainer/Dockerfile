# Kaziro dev container — omarchy-style terminal environment on Arch.
#
# No devcontainer features are used: the official docker-in-docker feature
# supports Debian/RHEL only, so docker is installed from Arch repos and
# started via docker-init.sh (postStartCommand, --privileged runArg).

FROM archlinux:latest

# --- omarchy repo bootstrap (same key steps as omarchy's own installer) ---
RUN pacman-key --init \
    && pacman-key --populate archlinux \
    && curl -fsSLo /tmp/omarchy.asc \
      'https://keys.openpgp.org/vks/v1/by-fingerprint/40DFB630FF42BCFFB047046CF0134EE680CAC571' \
    && pacman-key --add /tmp/omarchy.asc \
    && pacman-key --lsign-key 40DFB630FF42BCFFB047046CF0134EE680CAC571 \
    && printf '\n[omarchy]\nServer = https://pkgs.omarchy.org/stable/$arch\n' >> /etc/pacman.conf \
    && pacman -Sy --noconfirm archlinux-keyring omarchy-keyring

# --- omarchy base toolset + docker + 1Password CLI ---
RUN pacman -S --needed --noconfirm \
      zsh git rsync curl sudo openssh make less \
      starship fzf zoxide eza bat fd neovim atuin lazygit btop fastfetch gum yay \
      docker docker-compose docker-buildx \
      1password-cli \
      omarchy-settings herdr mise-bin \
    && ssh-keyscan -t ed25519 github.com >> /etc/ssh/ssh_known_hosts 2>/dev/null \
    && pacman -Scc --noconfirm

# --- dev user ---
# Seed the git identity in ~/.gitconfig: DevPod's credentials-server skips its
# fragile `su`-based identity setup (and the tunnel crashes that kill every
# ssh session) when the workspace user already has a git identity here.
RUN useradd --create-home --shell /usr/bin/zsh --groups docker dng \
    && printf 'dng ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/dng \
    && chmod 440 /etc/sudoers.d/dng \
    && printf '[user]\n\tname = Denis Gathondu\n\temail = denis@gathondu.com\n' > /home/dng/.gitconfig \
    && chown dng: /home/dng/.gitconfig

COPY docker-init.sh /usr/local/share/docker-init.sh
RUN chmod +x /usr/local/share/docker-init.sh

USER dng
WORKDIR /workspaces/kaziro
