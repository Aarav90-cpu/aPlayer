import '@material/web/button/filled-tonal-button.js';
import '@material/web/button/filled-button.js';
import '@material/web/button/text-button.js';
import '@material/web/icon/icon.js';
import '@material/web/iconbutton/icon-button.js';
import '@material/web/fab/fab.js';
import '@material/web/slider/slider.js';
import '@material/web/switch/switch.js';

let isPlaying = false;
let trackDuration = 0;
let updateInterval = null;
let catalog = [];

// Wavy Slider Logic
let wavyCtx = null;
let wavyCanvas = null;
let currentPos = 0;
let parsedLyrics = [];
let currentTrackIndex = -1;
let isLyricsVisible = false; // 0.0 to 1.0
let wavePhase = 0;

async function onPyWebviewReady() {
    console.log("JS: onPyWebviewReady started");
    document.getElementById('loader').style.display = 'none';
    document.getElementById('app').style.display = 'grid';
    initApp();
    
    // Load cached catalog
    console.log("JS: Calling pywebview.api.load_catalog()...");
    try {
        const cached = await window.pywebview.api.load_catalog();
        console.log("JS: Received catalog length:", cached ? cached.length : 'null');
        if (cached && cached.length > 0) {
            catalog = cached;
            renderCatalog();
        }
    } catch (e) {
        console.error("JS: Error in load_catalog():", e);
    }
    
    // Init theme
    const themeSwitch = document.getElementById('theme-switch');
    if ((await window.pywebview.api.get_setting('theme')) === 'dark') {
        document.body.classList.add('dark-theme');
        if(themeSwitch) themeSwitch.selected = true;
    }
}

if (window.pywebview) {
    onPyWebviewReady();
} else {
    window.addEventListener('pywebviewready', onPyWebviewReady);
}

function initApp() {
    console.log("JS: initApp started");
    // Navigation
    const sidebar = document.getElementById('sidebar');
    const views = document.querySelectorAll('.view');
    
    sidebar.addEventListener('click', (e) => {
        const item = e.target.closest('.nav-item');
        if (!item) return;

        const viewId = item.dataset.view;
        
        // Show view
        views.forEach(v => {
            v.classList.remove('active');
        });
        const viewEl = document.getElementById(`view-${viewId}`);
        if (viewEl) viewEl.classList.add('active');

        // Update nav UI by replacing elements
        document.querySelectorAll('.nav-item').forEach(nav => {
            const isCurrent = nav.dataset.view === viewId;
            const targetTag = isCurrent ? 'md-filled-tonal-button' : 'md-text-button';
            
            if (nav.tagName.toLowerCase() !== targetTag) {
                const newBtn = document.createElement(targetTag);
                newBtn.className = nav.className;
                if (isCurrent) {
                    newBtn.classList.add('active');
                } else {
                    newBtn.classList.remove('active');
                }
                newBtn.dataset.view = nav.dataset.view;
                newBtn.innerHTML = nav.innerHTML;
                nav.parentNode.replaceChild(newBtn, nav);
            }
        });
    });

    // Scanner
    const scanBtn = document.getElementById('scan-btn');
    scanBtn.addEventListener('click', async () => {
        const result = await window.pywebview.api.select_and_scan_folder();
        if (result.error) return; // cancelled
        
        catalog = result;
        renderCatalog();
    });

    // Player Controls
    
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

    const playPauseBtn = document.getElementById('play-pause-btn');
    const playPauseIcon = playPauseBtn.querySelector('md-icon');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    initWavySlider();

    playPauseBtn.addEventListener('click', async () => {
        const title = document.getElementById('current-title').textContent;
        if (title === 'No Track Selected') return;
        
        await window.pywebview.api.pause();
        const playing = await window.pywebview.api.is_playing();
        isPlaying = playing;
        playPauseIcon.textContent = isPlaying ? 'pause' : 'play_arrow';
    });

    prevBtn.addEventListener('click', () => console.log("Previous track"));
    nextBtn.addEventListener('click', () => console.log("Next track"));

    // Theme Toggle
    const themeSwitch = document.getElementById('theme-switch');
    if (themeSwitch) {
        const toggleTheme = () => {
            const isDark = themeSwitch.selected || themeSwitch.checked;
            if (isDark) {
                document.body.classList.add('dark-theme');
                window.pywebview.api.set_setting('theme', 'dark');
            } else {
                document.body.classList.remove('dark-theme');
                window.pywebview.api.set_setting('theme', 'light');
            }
        };
        themeSwitch.addEventListener('change', toggleTheme);
        themeSwitch.addEventListener('click', () => setTimeout(toggleTheme, 50));
    }
    console.log("JS: initApp finished successfully");
}

function renderCatalog() {
    renderHome();
    renderArtists();
    renderAlbums();
}

function createCard(title, subtitle, icon, cover, onClick) {
    const card = document.createElement('div');
    card.className = 'grid-card';
    
    let mediaHtml = `<span class="material-symbols-outlined">${icon}</span>`;
    if (cover) {
        mediaHtml = `<img src="/${cover}" alt="cover" loading="lazy">`;
    }
    
    card.innerHTML = `
        <div class="card-media">${mediaHtml}</div>
        <p class="card-title" title="${title}">${title}</p>
        <p class="card-subtitle" title="${subtitle}">${subtitle}</p>
    `;
    card.addEventListener('click', onClick);
    return card;
}

function renderHome() {
    const container = document.getElementById('catalog-grid');
    container.innerHTML = '';
    
    if (catalog.length === 0) {
        container.innerHTML = '<p class="empty-state">No music found.</p>';
        return;
    }

    catalog.forEach(track => {
        const card = createCard(track.title || track.filename, track.artist, 'audiotrack', track.cover, () => playTrack(track));
        container.appendChild(card);
    });
}

// Fetches and caches artist image URL to avoid hitting the API repeatedly
async function getArtistImageUrl(artist) {
    if (!artist || artist === 'Unknown Artist') return null;
    const cacheKey = `artist_url_${artist}`;
    let url = await window.pywebview.api.get_setting(cacheKey);
    if (url && url !== "null") return url;
    
    const result = await window.pywebview.api.fetch_artist_image(artist);
    if (result && result.url) {
        await window.pywebview.api.set_setting(cacheKey, result.url);
        return result.url;
    }
    return null;
}

async function renderArtists() {
    const container = document.getElementById('artists-grid');
    container.innerHTML = '';
    
    // Group by artist
    const artists = [...new Set(catalog.map(t => t.artist || 'Unknown Artist'))];
    
    for (const artist of artists) {
        const count = catalog.filter(t => (t.artist || 'Unknown Artist') === artist).length;
        const card = createCard(artist, `${count} tracks`, 'person', null, () => {
            // Future: Filter home view or open artist view
        });
        container.appendChild(card);
    }

    // Fetch images sequentially to avoid rate-limiting
    setTimeout(async () => {
        for (const artist of artists) {
            if (artist !== 'Unknown Artist') {
                const url = await getArtistImageUrl(artist);
                if (url) {
                    // Find card by its inner text matching the artist name
                    const allCards = container.querySelectorAll('.grid-card');
                    for (const card of allCards) {
                        if (card.querySelector('.card-title').textContent === artist) {
                            const mediaDiv = card.querySelector('.card-media');
                            mediaDiv.innerHTML = `<img src="${url}" alt="${artist}" loading="lazy">`;
                        }
                    }
                }
                // Rate limit delay (200ms)
                await new Promise(r => setTimeout(r, 200));
            }
        }
    }, 100);
}

function renderAlbums() {
    const container = document.getElementById('albums-grid');
    container.innerHTML = '';
    
    // Group by album
    const albums = [...new Set(catalog.map(t => t.album || 'Unknown Album'))];
    
    albums.forEach(album => {
        const count = catalog.filter(t => (t.album || 'Unknown Album') === album).length;
        const card = createCard(album, `${count} tracks`, 'album', null, () => {
            // Future: Filter home view or open album view
        });
        container.appendChild(card);
    });
}

async function playTrack(track) {
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
            const lines = lyricsRes.syncedLyrics.split('\n');
            let tempParsed = [];
            lines.forEach(line => {
                const match = line.match(/^\[(\d{2}):(\d{2}\.\d{2})\](.*)/);
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
async function startTracking() {
    if (updateInterval) clearInterval(updateInterval);
    
    setTimeout(async () => {
        trackDuration = await window.pywebview.api.get_length();
        if (trackDuration > 0) {
            document.getElementById('time-total').textContent = formatTime(trackDuration);
        }
    }, 500);

    updateInterval = setInterval(async () => {
        if (!isPlaying) return;
        
        const playing = await window.pywebview.api.is_playing();
        if (!playing) {
            isPlaying = false;
            document.querySelector('#play-pause-btn md-icon').textContent = 'play_arrow';
            return;
        }

        const pos = await window.pywebview.api.get_position(); 
        currentPos = pos;
        syncLyrics();
        
        if (trackDuration > 0) {
            document.getElementById('time-current').textContent = formatTime(pos * trackDuration);
        }
    }, 250);
}

function initWavySlider() {
    wavyCanvas = document.getElementById('wavy-slider');
    wavyCtx = wavyCanvas.getContext('2d');
    
    const resizeObserver = new ResizeObserver(() => {
        wavyCanvas.width = wavyCanvas.offsetWidth;
        wavyCanvas.height = wavyCanvas.offsetHeight;
    });
    resizeObserver.observe(wavyCanvas);
    
    wavyCanvas.addEventListener('click', async (e) => {
        if (!trackDuration) return;
        const rect = wavyCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const pos = Math.max(0, Math.min(1, x / rect.width));
        await window.pywebview.api.set_position(pos);
        currentPos = pos;
        syncLyrics();
    });
    
    requestAnimationFrame(drawWavySlider);
}

function drawWavySlider() {
    if (!wavyCanvas || !wavyCtx) return;
    
    const width = wavyCanvas.width;
    const height = wavyCanvas.height;
    
    if (width === 0 || height === 0) {
        requestAnimationFrame(drawWavySlider);
        return;
    }
    
    wavyCtx.clearRect(0, 0, width, height);
    
    const isDark = document.body.classList.contains('dark-theme');
    const primaryColor = isDark ? '#D0BCFF' : '#6750A4';
    const trackColor = isDark ? '#4F378B' : '#EADDFF';
    
    const midY = height / 2;
    const progressX = width * currentPos;
    
    if (isPlaying) {
        wavePhase += 0.05; // Slower
    }
    
    // Background track
    wavyCtx.beginPath();
    wavyCtx.moveTo(progressX, midY);
    wavyCtx.lineTo(width, midY);
    wavyCtx.strokeStyle = trackColor;
    wavyCtx.lineWidth = 4;
    wavyCtx.lineCap = 'round';
    wavyCtx.stroke();
    
    // Active wave
    wavyCtx.beginPath();
    wavyCtx.moveTo(0, midY);
    for (let x = 0; x <= progressX; x++) {
        const y = midY + Math.sin((x * 0.12) - wavePhase) * 6; // Squished width
        wavyCtx.lineTo(x, y);
    }
    wavyCtx.strokeStyle = primaryColor;
    wavyCtx.lineWidth = 4;
    wavyCtx.lineCap = 'round';
    wavyCtx.stroke();
    
    // Thumb ball
    const thumbY = progressX > 0 ? midY + Math.sin((progressX * 0.12) - wavePhase) * 6 : midY;
    wavyCtx.beginPath();
    wavyCtx.arc(progressX, thumbY, 8, 0, Math.PI * 2);
    wavyCtx.fillStyle = primaryColor;
    wavyCtx.fill();
    
    requestAnimationFrame(drawWavySlider);
}

function formatTime(ms) {
    if (ms < 0) return '0:00';
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}


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
