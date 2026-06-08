# Docker Usage Guide

## Building and Running with Docker

### Option 1: Using Docker Compose (Recommended)

1. **Build and start the container:**
   ```bash
   docker-compose up --build
   ```

2. **Run in detached mode:**
   ```bash
   docker-compose up -d --build
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the container:**
   ```bash
   docker-compose down
   ```

### Option 2: Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t youtube-to-mp3-suite .
   ```

2. **Run the container:**
   ```bash
   docker run -v $(pwd)/downloads:/mnt/UBERVAULT youtube-to-mp3-suite
   ```

## Volume Mapping

The Docker setup creates local directories that map to the container's download paths:

- `./downloads/Music` → `/mnt/UBERVAULT/Music`
- `./downloads/Video` → `/mnt/UBERVAULT/Video` 
- `./downloads/Torrents/Local` → `/mnt/UBERVAULT/Torrents/Local`

## Configuration

- Modify `playlists.yaml` to add/remove download sources
- The configuration file is mounted as read-only in the container
- Restart the container after making changes to `playlists.yaml`

## Scheduled Downloads

To run downloads periodically, uncomment the command line in `docker-compose.yml`:

```yaml
command: sh -c "while true; do python main.py; sleep 3600; done"
```

This will run the downloader every hour (3600 seconds).

## Troubleshooting

- Check container logs: `docker-compose logs`
- Ensure FFmpeg is working: `docker-compose exec youtube-downloader ffmpeg -version`
- Check Python dependencies: `docker-compose exec youtube-downloader pip list`
