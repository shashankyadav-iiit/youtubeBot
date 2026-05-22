# Setup Guide — Sleep Soundscape YouTube Bot

Generates long-form 4K relaxing soundscape videos (rain, ocean, fireplace,
white noise, …) and uploads them to YouTube automatically — one every 3 days,
fully hands-off via GitHub Actions.

## How it works
- **Visuals**: real 4K stock footage from the free Pexels API (falls back to an
  AI-generated still if no clip is found).
- **Audio**: 100% procedurally synthesized ambient sound — original on every
  render, so there is no "reused content" copyright risk.
- **Assembly**: a short seamless loop is stream-looped to the full length, so a
  3-hour 4K render stays fast.

---

## One-Time Setup

### Step 1: Install dependencies
```bash
cd nursery-rhyme-bot
pip3 install -r requirements.txt
brew install ffmpeg          # Mac   (Ubuntu: sudo apt-get install ffmpeg)
```

### Step 2: Create a new YouTube channel
Sleep content needs its own channel (separate from any kids content).
youtube.com → your account → **Create a channel** → e.g. "Calm Sleep Sounds".

### Step 3: Google Cloud — OAuth credentials
1. https://console.cloud.google.com/ → create/select a project
2. **APIs & Services → Library** → enable **YouTube Data API v3**
3. **OAuth consent screen** → **Publish app / set to "In production"**
   ⚠️ Critical: in "Testing" mode the login token expires after 7 days and the
   bot stops. "In production" makes it run indefinitely.
4. **Credentials → Create Credentials → OAuth client ID → Desktop app**
5. Download the JSON → save as `credentials/client_secret.json`

### Step 4: Authenticate
```bash
python3 youtube_uploader.py --auth
```
A browser opens — log in and **select the new sleep channel**.
Token is saved to `credentials/token.json` (keep secret).

### Step 5: Pexels API key (free stock video)
1. Sign up at https://www.pexels.com/api/
2. Copy your API key
3. For local testing, export it:
   ```bash
   export PEXELS_API_KEY="your_key_here"
   ```

### Step 6: Test with a dry run
```bash
python3 soundscape_audio.py --theme rain --preview     # listen: realistic rain?
python3 main.py --slot night --duration 1 --dry-run    # builds output_night.mp4
```
Watch `output_night.mp4` — confirm 1 hour, 4K, seamless loop, calm audio.

### Step 7: Test a private upload
```bash
python3 main.py --slot night --duration 1 --private
```
Check YouTube Studio: appears on the new channel, category **Music**, **not**
Made for Kids.

---

## GitHub Actions — Automatic Uploads

### Step 1: Push to GitHub & make the repo public
```bash
git add .
git commit -m "Sleep soundscape bot"
git push
```
Then repo → **Settings → General → Change visibility → Public**
(public repos get unlimited Actions minutes; credentials are gitignored).

### Step 2: Add repository secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `YOUTUBE_CLIENT_SECRET_B64` | `base64 -i credentials/client_secret.json` |
| `YOUTUBE_TOKEN_JSON_B64` | `base64 -i credentials/token.json` |
| `PEXELS_API_KEY` | your Pexels key |

### Step 3: Enable workflows
Repo → **Actions** tab → enable workflows.
`sleep_upload.yml` then runs **every 3 days** automatically (and can be
triggered manually with **Run workflow**).

---

## File Structure
```
main.py               # Orchestrator
script_generator.py   # Theme selection + no-repeat tracking
stock_video.py        # Pexels stock video fetch
image_generator.py    # AI still fallback
soundscape_audio.py   # Procedural ambient synthesis
video_generator.py    # Seamless loop assembly (ffmpeg)
seo_generator.py      # Sleep-niche title/description/tags
youtube_uploader.py   # YouTube API upload
data/
  soundscapes.json    # 14 soundscape themes
  uploaded.json       # Tracks used themes (auto-updated)
credentials/          # OAuth files (never commit)
.github/workflows/
  sleep_upload.yml    # Every-3-days upload job
```

## Notes
- Each upload costs ~1,600 YouTube API quota units (limit 10,000/day).
- When all 14 themes are used, the cycle auto-resets.
- A 3-hour 4K video is ~10–11 GB; the workflow frees disk space and writes to
  the large `/mnt` mount.

## Troubleshooting
- **"token expired"** → re-run `python3 youtube_uploader.py --auth`, update the
  `YOUTUBE_TOKEN_JSON_B64` secret. (Publishing the OAuth app prevents this.)
- **No stock video** → check `PEXELS_API_KEY`; the bot falls back to an AI still.
- **ffmpeg errors** → confirm `ffmpeg -version` works.
- **Disk space on CI** → the workflow's "Free up disk space" step handles it.
