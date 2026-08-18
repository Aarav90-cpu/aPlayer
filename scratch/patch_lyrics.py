import os
import re

js_path = '/home/aarav/aPlayer/ui/player_app.js'
with open(js_path, 'r') as f:
    js = f.read()

# Add variables at the top
if "let parsedLyrics = [];" not in js:
    js = js.replace("let currentPos = 0;", "let currentPos = 0;\nlet parsedLyrics = [];\nlet currentTrackIndex = -1;\nlet isLyricsVisible = false;")

# In initApp, add lyrics button listener
lyrics_btn_logic = """
    // Lyrics Overlay Toggle
    const lyricsBtn = document.getElementById('lyrics-btn');
    const lyricsOverlay = document.getElementById('lyrics-overlay');
    const closeLyricsBtn = document.getElementById('close-lyrics-btn');
    
    if (lyricsBtn) {
        lyricsBtn.addEventListener('click', () => {
            isLyricsVisible = true;
            lyricsOverlay.classList.add('show');
            syncLyrics(); // Sync immediately when opened
        });
    }
    if (closeLyricsBtn) {
        closeLyricsBtn.addEventListener('click', () => {
            isLyricsVisible = false;
            lyricsOverlay.classList.remove('show');
        });
    }
"""
if "lyricsBtn.addEventListener" not in js:
    js = js.replace("const playPauseBtn", lyrics_btn_logic + "\n    const playPauseBtn")

# Update playTrack to pre-fetch and fetch lyrics
play_track_match = re.search(r'async function playTrack\(track\) \{.*?(?=async function startTracking)', js, re.DOTALL)
if play_track_match:
    old_play = play_track_match.group(0)
    new_play = """async function playTrack(track) {
    currentTrackIndex = catalog.findIndex(t => t.path === track.path);
    const result = await window.pywebview.api.play(track.path);
    if (result.status === 'playing') {
        document.getElementById('current-title').textContent = track.title || track.filename;
        document.getElementById('current-artist').textContent = track.artist || 'Unknown Artist';
        
        const artMini = document.querySelector('.album-art-mini');
        
        // Fetch Album Cover (Fallback)
        const coverResult = await window.pywebview.api.fetch_album_cover(track.title || track.filename, track.artist || 'Unknown');
        if (coverResult && coverResult.url) {
            artMini.innerHTML = `<img src="${coverResult.url}" alt="cover">`;
        } else if (track.cover) {
            artMini.innerHTML = `<img src="/${track.cover}" alt="cover">`;
        } else {
            artMini.innerHTML = `<span class="material-symbols-outlined">music_note</span>`;
        }
        
        isPlaying = true;
        document.querySelector('#play-pause-btn md-icon').textContent = 'pause';
        
        startTracking();
        
        // Fetch lyrics
        const lyricsContent = document.getElementById('lyrics-content');
        lyricsContent.innerHTML = '<div class="spinner"></div><p>Loading Lyrics...</p>';
        parsedLyrics = [];
        const trackLen = await window.pywebview.api.get_length();
        const durationSec = trackLen > 0 ? Math.floor(trackLen / 1000) : 0;
        
        const lyricsRes = await window.pywebview.api.fetch_lyrics(track.title || track.filename, track.artist || 'Unknown', track.album || '', durationSec);
        
        lyricsContent.innerHTML = ''; // clear loader
        
        if (lyricsRes && lyricsRes.syncedLyrics) {
            // Parse LRC with translations
            const lines = lyricsRes.syncedLyrics.split('\\n');
            let tempParsed = [];
            lines.forEach(line => {
                const match = line.match(/^\\[(\\d{2}):(\\d{2}\\.\\d{2})\\](.*)/);
                if (match) {
                    const min = parseInt(match[1]);
                    const sec = parseFloat(match[2]);
                    const time = min * 60 + sec;
                    let text = match[3].trim();
                    
                    // Check if it's a translation of the exact same timestamp
                    if (tempParsed.length > 0 && Math.abs(tempParsed[tempParsed.length-1].time - time) < 0.05) {
                        tempParsed[tempParsed.length-1].translation = text;
                    } else {
                        tempParsed.push({ time, text, translation: '' });
                    }
                }
            });
            parsedLyrics = tempParsed;
            
            parsedLyrics.forEach((lrc, i) => {
                if (lrc.text === '') return;
                const p = document.createElement('p');
                p.className = 'lyric-line';
                p.id = `lrc-${i}`;
                if (lrc.translation) {
                    p.innerHTML = `${lrc.text}<span class="lyric-translation">${lrc.translation}</span>`;
                } else {
                    p.textContent = lrc.text;
                }
                p.addEventListener('click', async () => {
                    await window.pywebview.api.set_position(lrc.time / durationSec);
                    currentPos = lrc.time / durationSec;
                });
                lyricsContent.appendChild(p);
            });
            
        } else if (lyricsRes && lyricsRes.plainLyrics) {
            const p = document.createElement('p');
            p.className = 'lyric-line active';
            p.textContent = lyricsRes.plainLyrics;
            lyricsContent.appendChild(p);
        } else {
            lyricsContent.innerHTML = '<p class="empty-state">No lyrics found.</p>';
        }
        
        // Pre-fetch next and previous covers
        if (currentTrackIndex > 0) {
            const prev = catalog[currentTrackIndex - 1];
            window.pywebview.api.fetch_album_cover(prev.title || prev.filename, prev.artist || 'Unknown');
        }
        if (currentTrackIndex < catalog.length - 1) {
            const next = catalog[currentTrackIndex + 1];
            window.pywebview.api.fetch_album_cover(next.title || next.filename, next.artist || 'Unknown');
        }
    }
}
"""
    js = js.replace(old_play, new_play)

# Add sync function
sync_logic = """
function syncLyrics() {
    if (!isLyricsVisible || parsedLyrics.length === 0 || trackDuration === 0) return;
    
    const currentSec = currentPos * (trackDuration / 1000);
    let activeIndex = -1;
    
    for (let i = 0; i < parsedLyrics.length; i++) {
        if (currentSec >= parsedLyrics[i].time) {
            activeIndex = i;
        } else {
            break;
        }
    }
    
    if (activeIndex !== -1) {
        document.querySelectorAll('.lyric-line').forEach(el => el.classList.remove('active'));
        const activeEl = document.getElementById(`lrc-${activeIndex}`);
        if (activeEl) {
            activeEl.classList.add('active');
            // Auto scroll cinematic
            const container = document.getElementById('lyrics-content');
            const offset = activeEl.offsetTop - container.clientHeight / 2 + activeEl.clientHeight / 2;
            container.scrollTo({ top: offset, behavior: 'smooth' });
        }
    }
}
"""
if "function syncLyrics" not in js:
    js += "\n" + sync_logic

# Update startTracking to call syncLyrics
if "currentPos = pos;" in js:
    js = js.replace("currentPos = pos;", "currentPos = pos;\n        syncLyrics();")

# Next/Prev buttons
next_prev = """
    prevBtn.addEventListener('click', () => {
        if (currentTrackIndex > 0) playTrack(catalog[currentTrackIndex - 1]);
    });
    nextBtn.addEventListener('click', () => {
        if (currentTrackIndex < catalog.length - 1) playTrack(catalog[currentTrackIndex + 1]);
    });
"""
if "prevBtn.addEventListener('click', () => console.log" in js:
    js = re.sub(r'prevBtn\.addEventListener.*next track"\)\);', next_prev, js, flags=re.DOTALL)

with open(js_path, 'w') as f:
    f.write(js)
