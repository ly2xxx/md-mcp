# Docker Compose Guide

Quick reference for Docker Compose commands.

## Common Commands
- `docker-compose up -d` - Start containers in background
- `docker-compose down` - Stop and remove containers
- `docker-compose logs -f` - View live logs

## Example docker-compose.yml
```yaml
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
```
