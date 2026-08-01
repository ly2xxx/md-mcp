# Publishing the md-mcp Docker Image to Docker Hub

This guide details how to build and publish the **md-mcp** container image to a public Docker Hub repository for public consumption.

---

## Prerequisites

1. **Docker Hub Account**: Sign up at [hub.docker.com](https://hub.docker.com/) to obtain a username/namespace.
2. **Docker Desktop/Engine**: Ensure Docker is running locally.
3. **Run from Repo Root**: Always run build commands from the repository root (so the build context includes the `md_mcp` package).

---

## Step-by-Step Publishing

### Step 1: Log in to Docker Hub via CLI
Log in to your Docker Hub account from your terminal:

```powershell
docker login
```
*When prompted, enter your Docker Hub username. For the **Password** prompt, paste your **Personal Access Token (PAT)** instead of your account password.*

Alternatively, to avoid interactive input issues, you can log in by passing your PAT via standard input:
```powershell
"YOUR_PERSONAL_ACCESS_TOKEN" | docker login --username yourusername --password-stdin
```

---

### Step 2: Set up a Multi-Architecture Builder (Docker Buildx)
Public users may run on Intel/AMD (`amd64`) or Apple Silicon/ARM (`arm64`) architectures. Building a multi-platform image ensures it runs natively for everyone.

Enable and select a `buildx` builder:
```powershell
docker buildx create --name multi-builder --use
docker buildx inspect --bootstrap
```

---

### Step 3: Build and Push to Docker Hub
Run the build command from the **repository root**. Replace `yourusername` with your actual Docker Hub username.

```powershell
docker buildx build --platform linux/amd64,linux/arm64 `
  -f docker/Dockerfile `
  -t yourusername/md-mcp:latest `
  -t yourusername/md-mcp:1.0.4 `
  --push .
```

* **`--platform linux/amd64,linux/arm64`**: Compiles the image for both architectures.
* **`-t yourusername/md-mcp:latest`**: Tags it as the latest release.
* **`-t yourusername/md-mcp:1.0.0`**: A specific version tag (tied to your package release/git tag).
* **`--push`**: Pushes the compiled multi-arch manifest directly to Docker Hub.

To inspect the pushed multi-platform manifest and verify supported platforms:
```powershell
docker buildx imagetools inspect ly2xxx/md-mcp:latest
```

---

## Automating with GitHub Actions (Optional)

To automate publishing on new releases, add `.github/workflows/docker-publish.yml` to your repository:

```yaml
name: Publish Docker Image

on:
  release:
    types: [published]

jobs:
  push_to_registry:
    name: Push Docker image to Docker Hub
    runs-on: ubuntu-latest
    steps:
      - name: Check out the repo
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            yourusername/md-mcp:latest
            yourusername/md-mcp:${{ github.event.release.tag_name }}
```

---

## Verifying Public Consumption

Once pushed, users can reference the public image directly. For example, in their `claude_desktop_config.json`:

```json
"md-notes-docker": {
  "command": "docker",
  "args": [
    "run", "-i", "--rm",
    "-e", "MD_TRANSPORT=stdio",
    "-v", "C:/Users/you/notes:/data:ro",
    "yourusername/md-mcp:latest"
  ]
}
```
