# MDrop

**Self-hosted document → Markdown converter. No login. No data retention.**

[![Docker Hub](https://img.shields.io/docker/pulls/samapriya/mdrop?style=flat-square)](https://hub.docker.com/r/samapriya/mdrop)
[![Docker Image Size](https://img.shields.io/docker/image-size/samapriya/mdrop/latest?style=flat-square)](https://hub.docker.com/r/samapriya/mdrop)
[![GitHub](https://img.shields.io/github/license/samapriya/mdrop?style=flat-square)](https://github.com/samapriya/mdrop)
[![Build & Push to Docker Hub](https://github.com/samapriya/mdrop/actions/workflows/docker_publish.yml/badge.svg)](https://github.com/samapriya/mdrop/actions/workflows/docker_publish.yml)

Upload a PDF, Word doc, PowerPoint, spreadsheet, image, audio file, or any supported format. Get clean Markdown back. The original file is deleted the moment conversion finishes. The output is deleted the moment you download it. Nothing is ever written to disk.

---

## Deploy with Docker

### Option 1 — One-liner (quickest)

```bash
docker run -d \
  --name mdrop \
  --tmpfs /tmp/mdrop:size=1g \
  -p 8292:8000 \
  --restart unless-stopped \
  samapriya/mdrop:latest
```

Open **http://localhost:8292**

---

### Option 2 — Docker Compose

Save the following as `docker-compose.yml` and run `docker compose up -d`:

```yaml
services:
  mdrop:
    image: samapriya/mdrop:latest
    container_name: mdrop
    ports:
      - "8292:8000"
    tmpfs:
      - /tmp/mdrop:size=1g,mode=1777
    restart: unless-stopped
```

**Common commands:**

```bash
# Start
docker compose up -d

# Update to latest image
docker compose pull && docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f
```

---

### Option 3 — Portainer Stack

Portainer Stacks let you deploy and manage Docker Compose definitions directly from the Portainer UI — no SSH or CLI needed.

1. Log in to your Portainer instance
2. Go to **Stacks** → **Add stack**
3. Give it a name (e.g. `mdrop`)
4. Select **Web editor** and paste the following:

```yaml
services:
  mdrop:
    image: samapriya/mdrop:latest
    container_name: mdrop
    ports:
      - "8292:8000"
    tmpfs:
      - /tmp/mdrop:size=1g,mode=1777
    restart: unless-stopped
```

5. Click **Deploy the stack**
6. Open **http://your-server-ip:8292**

**To update the image in Portainer:**

Go to **Stacks** → select `mdrop` → click **Pull and redeploy**

> **Note on tmpfs in Portainer:** The `tmpfs` key is supported in Portainer stacks running on Linux hosts. If you see a warning or it fails, use the `--tmpfs` equivalent by replacing the `tmpfs` block with:
> ```yaml
>     volumes:
>       - type: tmpfs
>         target: /tmp/mdrop
>         tmpfs:
>           size: 1073741824  # 1GB in bytes
> ```

---

## Reverse Proxy Setup

MDrop listens internally on port **8000** and is mapped to **8292** on the host. Place any reverse proxy in front for HTTPS and custom domains — point it at `http://localhost:8292` (or `http://your-server-ip:8292`).

### Cloudflare Tunnel (free, no port forwarding needed)

```bash
cloudflared tunnel --url http://localhost:8292
```

Or in your Cloudflare Tunnel config:
```yaml
ingress:
  - hostname: mdrop.yourdomain.com
    service: http://localhost:8292
```

### Pangolin / Newt

Add MDrop as a new resource and point it to `http://localhost:8292`.

### Caddy

```
mdrop.yourdomain.com {
    reverse_proxy localhost:8292
}
```

### Nginx

```nginx
server {
    listen 80;
    server_name mdrop.yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass         http://localhost:8292;
        proxy_read_timeout 120s;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }
}
```

### Traefik

Add these labels to the `mdrop` service in your compose file:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.mdrop.rule=Host(`mdrop.yourdomain.com`)"
  - "traefik.http.routers.mdrop.entrypoints=websecure"
  - "traefik.http.routers.mdrop.tls.certresolver=letsencrypt"
  - "traefik.http.services.mdrop.loadbalancer.server.port=8000"
```

---

## Supported File Formats

| Category | Formats |
|---|---|
| Documents | PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS |
| Web | HTML, HTM |
| Data | CSV, JSON, XML |
| Images | JPG, JPEG, PNG, GIF, WEBP, BMP |
| Audio | WAV, MP3 (speech transcription) |
| Other | EPUB, ZIP, TXT, MD |

---

## File Size & Storage

- Maximum file size: **100MB** (aligns with Cloudflare's upload limit)
- All temporary files use RAM-only `tmpfs` — nothing is written to host disk
- Input file deleted immediately after conversion completes
- Output file deleted ~2 seconds after download begins

---

## Security Notes

- No authentication is built in — if exposing publicly, put it behind a VPN or an auth proxy (Authelia, Authentik, Cloudflare Access, etc.)
- No file content is ever logged — only filenames and sizes appear in server logs
- No database, no persistent storage, no cookies, no tracking

---

## Build from Source

```bash
git clone https://github.com/samapriya/mdrop.git
cd mdrop
docker compose up --build -d
```

---

## License

MIT · Powered by [MarkItDown](https://github.com/microsoft/markitdown) (Microsoft, MIT)
