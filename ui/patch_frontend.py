import re
import os

# 1. Update player.html
with open('/home/aarav/aPlayer/ui/player.html', 'r') as f:
    html = f.read()

lyrics_html = """
        <div id="lyrics-overlay" class="lyrics-overlay">
            <div class="lyrics-header">
                <md-icon-button id="close-lyrics-btn" aria-label="Close Lyrics">
                    <md-icon>keyboard_arrow_down</md-icon>
                </md-icon-button>
            </div>
            <div id="lyrics-content" class="lyrics-content">
                <p class="empty-state">No lyrics available</p>
            </div>
        </div>
"""

if "lyrics-overlay" not in html:
    html = html.replace('</body>', lyrics_html + '\n</body>')
    with open('/home/aarav/aPlayer/ui/player.html', 'w') as f:
        f.write(html)

# 2. Update player_style.css
with open('/home/aarav/aPlayer/ui/player_style.css', 'r') as f:
    css = f.read()

# Fix Wavy Slider container CSS to ensure visibility
if ".progress-container" in css:
    css = re.sub(r'\.progress-container\s*\{[^}]*\}', """.progress-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    width: 100%;
    height: 40px;
}""", css)

if "#wavy-slider" in css:
    css = re.sub(r'\#wavy-slider\s*\{[^}]*\}', """#wavy-slider {
    flex: 1;
    height: 40px;
    min-width: 300px;
    cursor: pointer;
}""", css)
else:
    css += """
#wavy-slider {
    flex: 1;
    height: 40px;
    min-width: 300px;
    cursor: pointer;
}
"""

if "lyrics-overlay" not in css:
    css += """
/* Lyrics Overlay */
.lyrics-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: calc(100% - 110px);
    background-color: var(--md-sys-color-surface-container);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    transform: translateY(100%);
    transition: transform 0.6s cubic-bezier(0.2, 0, 0, 1), opacity 0.6s;
    opacity: 0;
    pointer-events: none;
}
.lyrics-overlay.show {
    transform: translateY(0);
    opacity: 1;
    pointer-events: all;
}
.lyrics-header {
    padding: 24px;
    display: flex;
    justify-content: flex-start;
}
.lyrics-content {
    flex: 1;
    overflow-y: auto;
    padding: 0 10% 50vh 10%;
    display: flex;
    flex-direction: column;
    gap: 32px;
    align-items: flex-start;
    scroll-behavior: smooth;
    mask-image: linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%);
    -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%);
}
.lyrics-content::-webkit-scrollbar {
    display: none;
}
.lyric-line {
    font-size: 2.8rem;
    font-weight: 700;
    color: var(--md-sys-color-on-surface);
    opacity: 0.2;
    transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.2, 0, 0, 1), color 0.4s ease;
    transform-origin: left center;
    transform: scale(0.9);
    cursor: pointer;
    margin: 0;
}
.lyric-line.active {
    opacity: 1;
    transform: scale(1.0);
    color: var(--md-sys-color-primary);
}
.lyric-translation {
    font-size: 1.4rem;
    font-weight: 400;
    margin-top: 8px;
    opacity: 0.6;
    display: block;
}
"""

with open('/home/aarav/aPlayer/ui/player_style.css', 'w') as f:
    f.write(css)

# 3. Update player_app.js
with open('/home/aarav/aPlayer/ui/player_app.js', 'r') as f:
    js = f.read()

# Replace localStorage logic
js = js.replace("localStorage.getItem('theme') === 'dark'", "(await window.pywebview.api.get_setting('theme')) === 'dark'")
js = js.replace("localStorage.setItem('theme', 'dark')", "window.pywebview.api.set_setting('theme', 'dark')")
js = js.replace("localStorage.setItem('theme', 'light')", "window.pywebview.api.set_setting('theme', 'light')")

# Fix getArtistImageUrl
js = re.sub(r'async function getArtistImageUrl\(artist\) \{[\s\S]*?return null;\n\}', """async function getArtistImageUrl(artist) {
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
}""", js)

with open('/home/aarav/aPlayer/ui/player_app.js', 'w') as f:
    f.write(js)
