import re

with open('/home/aarav/aPlayer/bridge/main.py', 'r') as f:
    content = f.read()

new_methods = """
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
"""

content = content.replace("    def log_error(self, msg):", new_methods + "\n    def log_error(self, msg):")

with open('/home/aarav/aPlayer/bridge/main.py', 'w') as f:
    f.write(content)
