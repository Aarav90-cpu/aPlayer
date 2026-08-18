import webview
import threading
import os
import ctypes
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse
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
        pass

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
        import urllib.request
        import urllib.parse
        import urllib.error
        import re
        
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
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if "artists" in data and data["artists"] and data["artists"][0]:
                    img_url = data["artists"][0].get("strArtistBanner") or data["artists"][0].get("strArtistThumb")
                    if img_url:
                        urllib.request.urlretrieve(img_url, filepath)
                        return {"url": f"/.cache/artists/{filename}"}
        except Exception:
            pass
            
        # Fallback to v1
        try:
            with urllib.request.urlopen(f"https://www.theaudiodb.com/api/v1/json/123/search.php?s={encoded_artist}") as response:
                data = json.loads(response.read().decode())
                if data.get("artists") and data["artists"][0]:
                    img_url = data["artists"][0].get("strArtistBanner") or data["artists"][0].get("strArtistThumb")
                    if img_url:
                        urllib.request.urlretrieve(img_url, filepath)
                        return {"url": f"/.cache/artists/{filename}"}
        except Exception:
            pass
            
        return {"error": "Image not found"}


    def fetch_lyrics(self, track_name, artist_name, album_name="", duration=0):
        import urllib.request
        import urllib.parse
        import json
        
        query = {
            "track_name": track_name,
            "artist_name": artist_name
        }
        if album_name:
            query["album_name"] = album_name
        if duration and duration > 0:
            query["duration"] = int(duration)
            
        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, headers={"User-Agent": "aPlayer v1.0.0 (https://github.com)"})
        
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data
        except Exception as e:
            print("LRCLIB Error:", e)
            pass
        return {"error": "Lyrics not found"}

    def fetch_album_cover(self, track_name, artist_name):
        import urllib.request
        import urllib.parse
        import json
        import time
        import os
        import re
        
        # Clean inputs
        primary_artist = re.split(r'[/,&]|feat\.|ft\.', artist_name, flags=re.IGNORECASE)[0].strip()
        safe_name = "".join([c for c in f"{primary_artist}_{track_name}" if c.isalnum()]).rstrip()
        filename = f"{safe_name}.jpg"
        
        covers_dir = os.path.join(CACHE_DIR, 'covers')
        filepath = os.path.join(covers_dir, filename)
        
        if os.path.exists(filepath):
            return {"url": f"/.cache/covers/{filename}"}
            
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
            with urllib.request.urlopen(req) as response:
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
            with urllib.request.urlopen(caa_req) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as out:
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
            urllib.request.urlretrieve(caa_url, filepath)
            return {"url": f"/.cache/covers/{filename}"}
        except Exception:
            pass
            
        return {"error": "Cover not found"}


    def get_setting(self, key):
        import json, os
        s_file = os.path.join(CACHE_DIR, 'settings.json')
        if not os.path.exists(s_file):
            return None
        try:
            with open(s_file, 'r') as f:
                d = json.load(f)
                return d.get(key)
        except Exception:
            return None
            
    def set_setting(self, key, value):
        import json, os
        s_file = os.path.join(CACHE_DIR, 'settings.json')
        d = {}
        if os.path.exists(s_file):
            try:
                with open(s_file, 'r') as f:
                    d = json.load(f)
            except Exception:
                pass
        d[key] = value
        with open(s_file, 'w') as f:
            json.dump(d, f)
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
