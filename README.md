# Spotify to YouTube Music Transfer

This script pulls Liked Songs from **two different Spotify accounts**, deduplicates them (by ISRC or title & artist), and imports them into your **YouTube Music** account (either as a new playlist or directly into your Liked Songs library).

## Prerequisites

1. **Python 3.8+**
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setup & Authentication

### 1. Spotify API Credentials
1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log into either account.
2. Click **Create app**:
   - **App name**: `MusicTransfer`
   - **Redirect URI**: `http://localhost:8888/callback`
   - APIs used: **Web API**
3. Open your app settings and copy your **Client ID** and **Client Secret**.
4. Set them in your terminal:
   - **Windows (PowerShell)**:
     ```powershell
     $env:SPOTIFY_CLIENT_ID="your_client_id"
     $env:SPOTIFY_CLIENT_SECRET="your_client_secret"
     ```
   - **Linux/macOS**:
     ```bash
     export SPOTIFY_CLIENT_ID="your_client_id"
     export SPOTIFY_CLIENT_SECRET="your_client_secret"
     ```

### 2. YouTube Music Setup
Run the one-time authentication helper:
```bash
ytmusicapi oauth
```
Follow the URL and paste the verification code to generate `oauth.json` (or browser headers).

## Run the Script

```bash
python transfer.py
```
- A browser window will open for the first Spotify account — log in and authorize.
- A second browser window will open for the second Spotify account — log in and authorize.
- Choose whether to create a new playlist or add directly to Liked Songs.
- The script handles deduplication and automatic matching on YouTube Music.
