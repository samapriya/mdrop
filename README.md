# MDrop

**Self-hosted document → Markdown converter. No login. No data retention. Proxy-ready.**

[![Docker Hub](https://img.shields.io/docker/pulls/samapriya/mdrop?style=flat-square)](https://hub.docker.com/r/samapriya/mdrop)
[![GitHub](https://img.shields.io/github/license/samapriya/mdrop?style=flat-square)](https://github.com/samapriya/mdrop)
[![Build](https://github.com/samapriya/mdrop/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/samapriya/mdrop/actions/workflows/docker-publish.yml)

Drop in a PDF, Word doc, PowerPoint, spreadsheet, image, or audio file. Get clean Markdown out. Files are deleted from the server immediately — input on conversion, output on download.

---

## Quickstart (from Docker Hub — no build needed)

```bash
docker compose -f docker-compose.hub.yml up -d
```

Open **http://localhost:8000**

To update to the latest image:
```bash
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up -d
```

---

## Build from source

```bash
git clone https://github.com/samapriya/mdrop.git
cd mdrop
docker compose up --build -d
```

---

## Project Structure

```
mdrop/
├── .github/
│   └── workflows/
│       └── docker-publish.yml   # CI: builds & pushes to Docker Hub on push to main or tag
├── docker-compose.yml           # Build from source
├── docker-compose.hub.yml       # Pull from Docker Hub (end users)
├── .gitignore
├── README.md
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py                  # FastAPI: /convert, /download, serves frontend
    └── static/
        └── index.html           # Full frontend — edit to customise UI
```

---

## GitHub Actions Setup

The workflow builds and pushes to Docker Hub on every push to `main` and on version tags.

**Step 1 — Add secrets to your GitHub repo:**

Go to `github.com/samapriya/mdrop` → Settings → Secrets and variables → Actions → New repository secret

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `samapriya` |
| `DOCKERHUB_TOKEN` | your Docker Hub access token (see below) |

**Step 2 — Create a Docker Hub access token:**

1. Log in to [hub.docker.com](https://hub.docker.com)
2. Account Settings → Security → New Access Token
3. Name it `github-actions`, copy the token, paste as `DOCKERHUB_TOKEN`

**Step 3 — Push to trigger a build:**

```bash
git push origin main          # pushes samapriya/mdrop:latest
```

**Or tag a versioned release:**

```bash
git tag v1.0.0
git push origin v1.0.0        # pushes samapriya/mdrop:v1.0.0 + :latest
```

---

## Reverse Proxy Setup

MDrop is a single service on port 8000. Put any proxy in front:

**Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8000
```

**Caddy:**
```
yourdomain.com {
    reverse_proxy localhost:8000
}
```

**Nginx:**
```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_read_timeout 120s;
    client_max_body_size 100M;
}
```

**Traefik** — add to `docker-compose.hub.yml`:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.mdrop.rule=Host(`yourdomain.com`)"
  - "traefik.http.services.mdrop.loadbalancer.server.port=8000"
```

**Pangolin / Newt:** point resource to `http://localhost:8000`

---

## Supported Formats

PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS, HTML, CSV, JSON, XML, EPUB, ZIP, JPG, PNG, GIF, WEBP, BMP, WAV, MP3, TXT, MD

---

## Security

- All temp files use Docker `tmpfs` — RAM only, never written to host disk
- Input deleted immediately after conversion
- Output deleted ~2s after download begins
- No database, no content logs, no authentication required

---

## License

MIT · Powered by [MarkItDown](https://github.com/microsoft/markitdown) (Microsoft, MIT)
