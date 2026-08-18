import webview
import threading
import os
import ctypes
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse
import urllib.request
import urllib.error
import re
import time

# Load C library
libpath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../core/libplayer.so'))
libplayer = ctypes.CDLL(libpath)
libplayer.player_init.restype = None
libplayer.player_play.argtypes = [ctypes.c_char_p]
libplayer.player_pause.restype = None
libplayer.player_stop.restype = None
libplayer.player_is_playing.restype = ctypes.c_int
libplayer.player_get_position.restype = ctypes.c_float
libplayer.player_set_position.argtypes = [ctypes.c_float]
libplayer.player_get_length.restype = ctypes.c_longlong
libplayer.player_cleanup.restype = None
libplayer.player_set_volume.argtypes = [ctypes.c_int]
libplayer.player_set_volume.restype = None
libplayer.player_set_spatializer.argtypes = [ctypes.c_int]
libplayer.player_set_spatializer.restype = None

libplayer.scanner_scan_folder.argtypes = [ctypes.c_char_p]
libplayer.scanner_scan_folder.restype = ctypes.c_void_p
libplayer.scanner_free_result.argtypes = [ctypes.c_void_p]
libplayer.scanner_free_result.restype = None

libplayer.player_init()

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.cache'))
COVERS_DIR = os.path.join(CACHE_DIR, 'covers')
os.makedirs(COVERS_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, 'catalog.json')

class Api:
    def __init__(self):
        self._settings_lock = threading.Lock()

    def play(self, filepath=None):
        if not filepath:
            # Open file dialog for single file playback
            result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=('Audio Files (*.mp3;*.wav;*.flac;*.ogg;*.m4a)', 'All files (*.*)'))
            if result and len(result) > 0:
                filepath = result[0]
            else:
                return {"error": "No file selected"}
        
        libplayer.player_play(filepath.encode('utf-8'))
        return {"status": "playing", "file": filepath}

    def pause(self):
        libplayer.player_pause()
        return {"status": "paused_or_resumed"}

    def stop(self):
        libplayer.player_stop()
        return {"status": "stopped"}

    def is_playing(self):
        return bool(libplayer.player_is_playing())

    def get_position(self):
        return libplayer.player_get_position()

    def set_position(self, pos):
        libplayer.player_set_position(float(pos))

    def get_length(self):
        return libplayer.player_get_length()

    def set_volume(self, volume):
        libplayer.player_set_volume(int(volume))
        return True

    def set_spatial_audio(self, enabled):
        libplayer.player_set_spatializer(1 if enabled else 0)
        return True

    def select_and_scan_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            folder_path = result[0]
            ptr = libplayer.scanner_scan_folder(folder_path.encode('utf-8'))
            if ptr:
                json_bytes = ctypes.cast(ptr, ctypes.c_char_p).value
                json_str = json_bytes.decode('utf-8')
                libplayer.scanner_free_result(ptr)
                
                # Cache it
                with open(CACHE_FILE, 'w') as f:
                    f.write(json_str)
                
                return json.loads(json_str)
        return {"error": "No folder selected"}
        
    def load_catalog(self):
        print("API: load_catalog() called")
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                data = json.loads(f.read())
                print(f"API: load_catalog() returning {len(data)} items")
                return data
        print("API: load_catalog() returning [] because cache file does not exist")
        return []

    def fetch_artist_image(self, artist_name):
        artist_dir = os.path.join(CACHE_DIR, 'artists')
        os.makedirs(artist_dir, exist_ok=True)
        
        # Extract primary artist before any /, ',', '&', 'feat.', 'ft.'
        primary_artist = re.split(r'[/,&]|feat\.|ft\.', artist_name, flags=re.IGNORECASE)[0].strip()
        safe_name = "".join([c for c in primary_artist if c.isalnum() or c==' ']).rstrip()
        filename = f"{safe_name}.jpg"
        filepath = os.path.join(artist_dir, filename)
        
        if os.path.exists(filepath):
            return {"url": f"/.cache/artists/{filename}"}
            
        encoded_artist = urllib.parse.quote(primary_artist)
        
        # Try v2 first
        req = urllib.request.Request(
            f"https://www.theaudiodb.com/api/v2/json/search/artist/{encoded_artist}",
            headers={"X-API-KEY": "123"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if "artists" in data and data["artists"] and data["artists"][0]:
                    img_url = data["artists"][0].get("strArtistBanner") or data["artists"][0].get("strArtistThumb")
                    if img_url:
                        urllib.request.urlretrieve(img_url, filepath)
                        return {"url": f"/.cache/artists/{filename}"}
        except Exception as e:
            print(f"fetch_artist_image v2 error: {e}")
            
        # Fallback to v1
        try:
            with urllib.request.urlopen(f"https://www.theaudiodb.com/api/v1/json/123/search.php?s={encoded_artist}", timeout=5) as response:
                data = json.loads(response.read().decode())
                if data.get("artists") and data["artists"][0]:
                    img_url = data["artists"][0].get("strArtistBanner") or data["artists"][0].get("strArtistThumb")
                    if img_url:
                        urllib.request.urlretrieve(img_url, filepath)
                        return {"url": f"/.cache/artists/{filename}"}
        except Exception as e:
            print(f"fetch_artist_image v1 error: {e}")
            
        return {"error": "Image not found"}


    def fetch_lyrics(self, track_name, artist_name, album_name="", duration=0):
        safe_name = "".join([c for c in f"{artist_name}_{track_name}" if c.isalnum()]).rstrip()
        lyrics_dir = os.path.join(CACHE_DIR, 'lyrics')
        os.makedirs(lyrics_dir, exist_ok=True)
        cache_path = os.path.join(lyrics_dir, f"{safe_name}.json")
        
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
                
        def do_req(url):
            req = urllib.request.Request(url, headers={"User-Agent": "aPlayer v1.0.0 (https://github.com)"})
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        return json.loads(response.read().decode())
            except Exception as e:
                print(f"fetch_lyrics error for {url}: {e}")
            return None

        # Try 1: Exact match with all metadata
        query1 = {"track_name": track_name, "artist_name": artist_name}
        if album_name: query1["album_name"] = album_name
        if duration and duration > 0: query1["duration"] = int(duration)
        url1 = "https://lrclib.net/api/get?" + urllib.parse.urlencode(query1)
        res1 = do_req(url1)
        if res1 and (res1.get('syncedLyrics') or res1.get('plainLyrics')):
            with open(cache_path, 'w') as f: json.dump(res1, f)
            return res1

        # Try 2: Exact match without album/duration
        query2 = {"track_name": track_name, "artist_name": artist_name}
        url2 = "https://lrclib.net/api/get?" + urllib.parse.urlencode(query2)
        res2 = do_req(url2)
        if res2 and (res2.get('syncedLyrics') or res2.get('plainLyrics')):
            with open(cache_path, 'w') as f: json.dump(res2, f)
            return res2

        # Try 3: Search endpoint
        query3 = {"q": f"{track_name} {artist_name}"}
        url3 = "https://lrclib.net/api/search?" + urllib.parse.urlencode(query3)
        res3 = do_req(url3)
        if res3 and isinstance(res3, list) and len(res3) > 0:
            for item in res3:
                if item.get('syncedLyrics'):
                    with open(cache_path, 'w') as f: json.dump(item, f)
                    return item
            with open(cache_path, 'w') as f: json.dump(res3[0], f)
            return res3[0] # Fallback to first even if no syncedLyrics

        return {"error": "Lyrics not found"}



    def fetch_album_cover(self, track_name, artist_name, filepath=None):
        # Clean inputs
        primary_artist = re.split(r'[/,&]|feat\.|ft\.', artist_name, flags=re.IGNORECASE)[0].strip()
        safe_name = "".join([c for c in f"{primary_artist}_{track_name}" if c.isalnum()]).rstrip()
        filename = f"{safe_name}.jpg"
        
        covers_dir = os.path.join(CACHE_DIR, 'covers')
        cached_filepath = os.path.join(covers_dir, filename)
        
        if os.path.exists(cached_filepath):
            return {"url": f"/.cache/covers/{filename}"}
            
        # Try to extract embedded cover
        if filepath and os.path.exists(filepath):
            try:
                import mutagen
                audio = mutagen.File(filepath)
                if audio:
                    artwork_data = None
                    if hasattr(audio, 'tags') and audio.tags:
                        if 'APIC:' in audio.tags: # ID3v2
                            apic = audio.tags.getall('APIC:')
                            if apic: artwork_data = apic[0].data
                        elif 'covr' in audio.tags: # MP4/M4A
                            artwork_data = audio.tags['covr'][0]
                        elif 'METADATA_BLOCK_PICTURE' in audio.tags: # FLAC
                            pics = audio.tags.get('METADATA_BLOCK_PICTURE')
                            if pics: artwork_data = pics[0].data
                            
                    if not artwork_data and hasattr(audio, 'pictures') and audio.pictures:
                        artwork_data = audio.pictures[0].data
                    
                    if artwork_data:
                        with open(cached_filepath, 'wb') as img:
                            img.write(artwork_data)
                        return {"url": f"/.cache/covers/{filename}"}
            except Exception as e:
                print("Mutagen embedded art error:", e)
                
        # 1. Search MusicBrainz to get MBID
        query = f'recording:"{track_name}" AND artist:"{primary_artist}"'
        url = "https://musicbrainz.org/ws/2/recording?query=" + urllib.parse.quote(query) + "&fmt=json"
        req = urllib.request.Request(url, headers={"User-Agent": "aPlayer v1.0.0 (https://github.com)"})
        
        # Rate limit MB
        if hasattr(self, '_last_mb_req'):
            elapsed = time.time() - self._last_mb_req
            if elapsed < 1.1:
                time.sleep(1.1 - elapsed)
        
        mbid = None
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                self._last_mb_req = time.time()
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if data.get("recordings") and len(data["recordings"]) > 0:
                        for rec in data["recordings"]:
                            if "releases" in rec and len(rec["releases"]) > 0:
                                mbid = rec["releases"][0]["id"]
                                break
        except Exception as e:
            print("MusicBrainz Error:", e)
            return {"error": "MBID not found"}
            
        if not mbid:
            return {"error": "MBID not found"}
            
        # 2. Fetch Cover Art Archive
        caa_url = f"https://coverartarchive.org/release/{mbid}/front"
        caa_req = urllib.request.Request(caa_url, headers={"User-Agent": "aPlayer v1.0.0 (https://github.com)"})
        try:
            with urllib.request.urlopen(caa_req, timeout=5) as response:
                if response.status == 200:
                    with open(cached_filepath, 'wb') as out:
                        out.write(response.read())
                    return {"url": f"/.cache/covers/{filename}"}
        except urllib.error.HTTPError as e:
            # 404 is common if no cover exists, or 307 redirect
            # urlretrieve handles 307 automatically usually
            pass
        except Exception as e:
            print("CoverArtArchive Error:", e)
            
        # Try urlretrieve if redirect failed above
        try:
            urllib.request.urlretrieve(caa_url, cached_filepath)
            return {"url": f"/.cache/covers/{filename}"}
        except Exception as e:
            print(f"urlretrieve error: {e}")
            
        return {"error": "Cover not found"}


    def get_setting(self, key):
        s_file = os.path.join(CACHE_DIR, 'settings.json')
        if not os.path.exists(s_file):
            return None
        with self._settings_lock:
            try:
                with open(s_file, 'r') as f:
                    d = json.load(f)
                    return d.get(key)
            except Exception as e:
                print(f"get_setting error: {e}")
                return None
            
    def set_setting(self, key, value):
        s_file = os.path.join(CACHE_DIR, 'settings.json')
        with self._settings_lock:
            d = {}
            if os.path.exists(s_file):
                try:
                    with open(s_file, 'r') as f:
                        d = json.load(f)
                except Exception as e:
                    print(f"set_setting load error: {e}")
            d[key] = value
            try:
                with open(s_file, 'w') as f:
                    json.dump(d, f)
            except Exception as e:
                print(f"set_setting save error: {e}")
        return True

    def log_error(self, msg):
        print(f"JS ERROR: {msg}")
        return {}

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def translate_path(self, path):
        path = super().translate_path(path)
        return path

def start_server(server):
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    server.serve_forever()

if __name__ == '__main__':
    # Bind to port 0 to let the OS assign an available dynamic port.
    # This prevents "Address already in use" errors on restart.
    server = HTTPServer(('127.0.0.1', 0), CORSRequestHandler)
    port = server.server_port
    
    t = threading.Thread(target=start_server, args=(server,), daemon=True)
    t.start()

    api = Api()
    window = webview.create_window(
        'aPlayer - Linux Music Player', 
        f'http://127.0.0.1:{port}/ui/player.html', 
        js_api=api, 
        width=1000, 
        height=800
    )
    
    webview.start(debug=False)
    
    libplayer.player_cleanup()
