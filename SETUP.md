# Setup Guide — Nursery Rhyme YouTube Shorts Bot

## One-Time Setup (15 minutes)

### Step 1: Install Python Dependencies
```bash
cd nursery-rhyme-bot
pip3 install -r requirements.txt
```

### Step 2: Install FFmpeg (required by MoviePy)
```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### Step 3: Download Royalty-Free Background Music
1. Go to https://pixabay.com/music/
2. Search: "nursery rhyme background", "kids music", "children melody"
3. Download 5–10 tracks as MP3
4. Place them in `data/music/`

The font (Fredoka One) is auto-downloaded on first run.

### Step 4: Google Cloud Console Setup
1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "NurseryRhymeBot")
3. Go to **APIs & Services → Library**
4. Search and enable: **YouTube Data API v3**
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → OAuth client ID**
7. Application type: **Desktop app**
8. Download the JSON file → save as `credentials/client_secret.json`

### Step 5: Authenticate with YouTube (one-time browser login)
```bash
python3 youtube_uploader.py --auth
```
This opens a browser window. Log in with your YouTube channel account.
Token is saved to `credentials/token.json` — keep this secret!

### Step 6: Test with a Dry Run
```bash
python3 main.py --slot morning --dry-run
```
This generates `output_morning.mp4` without uploading. Watch it to verify quality.

### Step 7: Test Upload as Private
```bash
python3 main.py --slot morning --private
```
Check YouTube Studio to confirm the video looks correct.

---

## GitHub Actions Setup (for automatic daily uploads)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial nursery rhyme bot"
git remote add origin https://github.com/YOUR_USERNAME/nursery-rhyme-bot.git
git push -u origin main
```

### Step 2: Add GitHub Secrets
Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these two secrets:

**YOUTUBE_CLIENT_SECRET_B64**
```bash
base64 -i credentials/client_secret.json | pbcopy   # Mac (copies to clipboard)
```

**YOUTUBE_TOKEN_JSON_B64**
```bash
base64 -i credentials/token.json | pbcopy   # Mac (copies to clipboard)
```

### Step 3: Enable Workflows
Go to your repo → **Actions tab** → Enable workflows if prompted.

The 5 workflows will now run automatically every day:
- Dawn: 6am EST
- Morning: 9am EST
- Afternoon: 1pm EST
- After School: 4pm EST
- Evening: 7pm EST

---

## File Structure
```
nursery-rhyme-bot/
├── main.py                  # Entry point
├── script_generator.py      # Rhyme selection
├── audio_generator.py       # TTS + music mixing
├── image_generator.py       # Pollinations.ai scene images
├── video_generator.py       # Ken Burns + karaoke + sparkles
├── seo_generator.py         # SEO title/description/tags
├── youtube_uploader.py      # YouTube API upload
├── data/
│   ├── rhymes.json          # 55+ nursery rhymes database
│   ├── uploaded.json        # Tracks uploaded rhymes
│   └── music/               # Your MP3 background tracks (add manually)
├── assets/fonts/            # Auto-downloaded on first run
├── credentials/             # OAuth files (never commit these!)
├── temp/                    # Auto-cleaned after each run
└── .github/workflows/       # 5 scheduled upload jobs
```

---

## Important Notes
- **credentials/** folder is gitignored — never commit OAuth tokens
- `data/uploaded.json` is auto-updated by GitHub Actions after each upload
- When all 55 rhymes are used, the cycle resets automatically
- Each upload costs ~1,600 YouTube API quota units; 5/day = 8,000 (limit is 10,000)
- Videos are marked `selfDeclaredMadeForKids = True` for YouTube Kids compliance

## Troubleshooting
- **"quota exceeded"**: You've hit the 10,000 unit/day limit. Wait until next day.
- **"token expired"**: Re-run `python youtube_uploader.py --auth` and update the GitHub secret.
- **MoviePy errors**: Make sure ffmpeg is installed (`ffmpeg -version`).
- **Pollinations timeout**: The fallback generates a solid gradient background instead.
