#!/usr/bin/env bash
# ==============================================================================
# Install the lab attack tooling + targets for the SOC Manager demo.
# Requires sudo. Run ONCE. Authorized lab use only (your own VM).
# ==============================================================================
set -e

echo "[*] Installing attack tools and targets (sudo required)..."
sudo apt update
sudo apt install -y \
    openssh-server \
    nmap hydra hping3 \
    docker.io

echo "[*] Enabling services..."
sudo systemctl enable --now ssh
sudo systemctl enable --now docker

echo "[*] Launching OWASP Juice Shop (web-attack playground) on :3000..."
if ! sudo docker ps -a --format '{{.Names}}' | grep -q '^juiceshop$'; then
    sudo docker run -d --restart unless-stopped -p 3000:3000 \
         --name juiceshop bkimminich/juice-shop
else
    sudo docker start juiceshop || true
fi

cat <<'EOF'

----------------------------------------------------------------------
 Lab ready. Targets:
   - SSH            : localhost:22   (brute-force target)
   - Juice Shop     : http://localhost:3000  (web playground / scan+flood target)

 Attack commands (point the SOC monitor at the port first):
   SSH brute force -> brute_force:
     curl -X POST http://localhost:8000/api/traffic/port -d '{"port":22}' \
          -H 'Content-Type: application/json'
     printf 'admin\nroot\npassword\n123456\n' > /tmp/wl.txt
     hydra -l testuser -P /tmp/wl.txt ssh://localhost

   Port scan -> recon:
     curl -X POST http://localhost:8000/api/traffic/port -d '{"port":3000}' \
          -H 'Content-Type: application/json'
     nmap -sS -T4 localhost -p 3000

   Flood -> dos_flood:
     sudo hping3 -S --flood -p 3000 localhost     # Ctrl-C after ~10s

 Then watch:  curl -s http://localhost:8000/api/incidents
----------------------------------------------------------------------
EOF
