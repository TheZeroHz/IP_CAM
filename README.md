# ESP32-S3 Camera Relay (Flask + Render)

Streams OV2640 JPEG frames from one or more ESP32-S3 boards to a
public HTTPS endpoint on Render.

## Endpoints

| Verb | Route      | Purpose                             |
|------|------------|-------------------------------------|
| POST | /upload    | ESP32 uploads a JPEG frame          |
| GET  | /stream    | Browser MJPEG stream                |
| GET  | /          | Minimal HTML viewer                 |

## Deploy

```bash
git clone https://github.com/you/esp32-cam-relay.git
cd esp32-cam-relay
# push to your own GitHub/GitLab
