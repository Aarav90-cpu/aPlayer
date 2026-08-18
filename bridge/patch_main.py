import re

with open('/home/aarav/aPlayer/bridge/main.py', 'r') as f:
    content = f.read()

new_methods = """
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
"""

# Insert methods before log_error
content = content.replace("    def log_error(self, msg):", new_methods + "\n    def log_error(self, msg):")

with open('/home/aarav/aPlayer/bridge/main.py', 'w') as f:
    f.write(content)
