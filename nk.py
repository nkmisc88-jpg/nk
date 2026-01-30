import requests
import re
import datetime
import os
import sys

# ==========================================
# CONFIGURATION
# ==========================================
# CHANGED: Output file name updated
OUTPUT_FILE = "nk.m3u"

# --- UPDATED FILE NAMES ---
YOUTUBE_FILE = "Temporary.txt"
MPD_FILE = "media presentation description.txt"  

POCKET_URL = "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/main/index.html" 

# --- NEW SOURCES ---
ZEE_JOKER_URL = "https://raw.githubusercontent.com/tiger629/m3u/refs/heads/main/joker.m3u"
YOUTUBE_LIVE_URL = "https://raw.githubusercontent.com/nkmisc88-jpg/my-youtube-live-playlist/refs/heads/main/playlist.m3u"
FANCODE_URL = "https://raw.githubusercontent.com/Jitendra-unatti/fancode/main/data/fancode.m3u"
SONY_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
ZEE_LIVE_URL = "https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"
JIO_WORKER_URL = "https://jiohotstar.joker-verse.workers.dev/joker.m3u8"

# --- JIO HOTSTAR CONFIG ---
JIO_EVENTS_JSON = "https://raw.githubusercontent.com/DebugDyno/yo_events/refs/heads/main/jiohotstar.json"
JIO_COOKIE_JSON = "https://raw.githubusercontent.com/kajju027/Jiohotstar-Events-Json/refs/heads/main/jiotv.json"
JIO_BASE_STREAM = "https://jiohotstar.joker-verse.workers.dev/joker/stream"
JIO_UID_PASS = "uid=706298993&pass=ef2678f2"
JIO_UA = "Hotstar;in.startv.hotstar/25.01.27.5.3788 (Android/13)"
JIO_REF = "https://www.hotstar.com/"

# 2. GROUP MAPPING
MOVE_TO_TAMIL_HD = ["Sun TV HD", "Star Vijay HD", "Colors Tamil HD", "Zee Tamil HD", "KTV HD", "Sun Music HD", "Jaya TV HD", "Zee Thirai HD", "Vijay Super HD"]
MOVE_TO_TAMIL_NEWS = ["Sun News", "News7 Tamil", "Thanthi TV", "Raj News 24x7", "Tamil Janam", "Jaya Plus", "M Nadu", "News J", "News18 Tamil Nadu", "News Tamil 24x7", "Win TV", "Zee Tamil News", "Polimer News", "Puthiya Thalaimurai", "Seithigal TV", "Sathiyam TV", "MalaiMurasu Seithigal"]
MOVE_TO_INFOTAINMENT_SD = ["GOOD TiMES", "Food Food"]

# CHANGED: Removed Sony Ten channels from the Keep list
SPORTS_HD_KEEP = ["Star Sports 1 HD", "Star Sports 2 HD", "Star Sports 1 Tamil HD", "Star Sports 2 Tamil HD", "Star Sports Select 1 HD", "Star Sports Select 2 HD"]

INFOTAINMENT_KEYWORDS = ["discovery", "animal planet", "nat geo", "history tv", "tlc", "bbc earth", "sony bbc", "fox life", "travelxp"]

# 3. DELETE LIST
# CHANGED: Added "sony ten" to be deleted
BAD_KEYWORDS = ["fashion", "overseas", "yupp", "usa", "pluto", "sun nxt", "sunnxt", "jio specials hd", "zee devotional", "extras", "local channels", "sony ten"]

# 4. AUTO LOGO
LOGO_MAP = {"willow": "https://i.imgur.com/39s1fL3.png", "fox": "https://i.imgur.com/39s1fL3.png"}
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_group_and_name(line):
    grp_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
    group = grp_match.group(1).strip() if grp_match else ""
    name = line.split(",")[-1].strip()
    return group, name

def should_keep_channel(group, name):
    check_str = (group + " " + name).lower()
    for bad in BAD_KEYWORDS:
        if bad in check_str: return False 
    return True

def get_clean_id(name):
    name = name.lower().replace("hd", "").replace(" ", "").strip()
    return re.sub(r'[^a-z0-9]', '', name)

def fetch_raw_lines(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200:
            return r.text.splitlines()
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
    return []

def fetch_live_events(url, force_group="Live Events"):
    lines = []
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            content = r.text.splitlines()
            for line in content:
                line = line.strip()
                if not line: continue
                if line.startswith("#EXTM3U"): continue
                if line.startswith("#EXTINF"):
                    line = re.sub(r'group-title="([^"]*)"', '', line)
                    line = re.sub(r'(#EXTINF:[-0-9]+)', f'\\1 group-title="{force_group}"', line)
                    lines.append(line)
                elif not line.startswith("#"):
                    lines.append(line)
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
    return lines

# === RECURSIVE COOKIE FINDER ===
def find_cookie_recursive(data):
    if isinstance(data, dict):
        for k in ["cookie", "Cookie", "token", "Token"]:
            if k in data and isinstance(data[k], str):
                return data[k]
        for v in data.values():
            found = find_cookie_recursive(v)
            if found: return found
    elif isinstance(data, list):
        for item in data:
            found = find_cookie_recursive(item)
            if found: return found
    elif isinstance(data, str):
        if "__hdnea__" in data:
            return data
    return None

# === JIO HOTSTAR FETCHER (UPDATED) ===
def fetch_jio_hotstar_live():
    lines = []
    print("📥 Fetching JioHotstar Live Events...")
    try:
        # 1. Fetch Cookie
        cookie_val = ""
        c_data = None
        try:
            c_resp = requests.get(JIO_COOKIE_JSON, headers={"User-Agent": UA_HEADER}, timeout=10)
            if c_resp.status_code == 200:
                c_data = c_resp.json()
        except Exception as e:
            print(f"⚠️ Error fetching Jio Cookie: {e}")
            return []

        if c_data is None: return []

        raw_cookie = find_cookie_recursive(c_data)
        if not raw_cookie:
            print("⚠️ FATAL: No cookie found.")
            return []
            
        cookie_val = raw_cookie.strip().replace('"', '').replace('\\"', '').replace('}', '').replace('{', '')

        # 2. Fetch Events
        e_resp = requests.get(JIO_EVENTS_JSON, headers={"User-Agent": UA_HEADER}, timeout=10)
        if e_resp.status_code != 200:
            print("⚠️ Failed to fetch Jio Events JSON")
            return []
        
        events = e_resp.json()
        if isinstance(events, dict):
            events = events.get("items", []) or events.get("events", []) or events.get("data", [])

        count = 0
        for event in events:
            vid_id = event.get("id") or event.get("contentId") or event.get("ID")
            title = event.get("name") or event.get("title") or event.get("eventName") or "Jio Event"
            logo = event.get("logo") or event.get("image") or event.get("thumbnail") or ""
            
            if not vid_id: continue

            # --- 1. PARSE LANGUAGES FIRST ---
            langs_data = event.get("languages") or event.get("language") or event.get("lang")
            processed_langs = []

            if isinstance(langs_data, dict):
                for name, code in langs_data.items():
                    processed_langs.append((code, name))
            elif isinstance(langs_data, list):
                for code in langs_data:
                    processed_langs.append((code, code.upper()))
            elif isinstance(langs_data, str):
                parts = [x.strip() for x in langs_data.split(",")]
                for p in parts:
                    processed_langs.append((p, p.upper()))
            else:
                processed_langs.append(("eng", "English"))

            # --- 2. CONDITIONALLY ADD MULTI-AUDIO ---
            if len(processed_langs) > 1:
                default_stream_url = (
                    f'{JIO_BASE_STREAM}?id={vid_id}&{JIO_UID_PASS}'
                    f'|Cookie="{cookie_val}"&User-Agent="{JIO_UA}"&Referer="{JIO_REF}"'
                )
                default_display_name = f"JioHotstar: [Multi-Audio] {title}"
                lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{logo}",{default_display_name}')
                lines.append(default_stream_url)
                count += 1

            # --- 3. ADD SPECIFIC LANGUAGES ---
            for lang_code, lang_name in processed_langs:
                stream_url = (
                    f'{JIO_BASE_STREAM}?id={vid_id}&lang={lang_code}&{JIO_UID_PASS}'
                    f'|Cookie="{cookie_val}"&User-Agent="{JIO_UA}"&Referer="{JIO_REF}"'
                )
                display_name = f"JioHotstar: [{lang_name}] {title}"
                lines.append(f'#EXTINF:-1 group-title="Live Events" tvg-logo="{logo}",{display_name}')
                lines.append(stream_url)
                count += 1
        
        print(f"   --> Generated {count} JioHotstar lines.")

    except Exception as e:
        print(f"⚠️ Critical Error in JioHotstar Fetcher: {e}")
    
    return lines

def get_auto_logo(channel_name):
    name_lower = channel_name.lower()
    for key, url in LOGO_MAP.items():
        if key in name_lower:
            return url
    return ""

def parse_youtube_txt():
    lines = []
    # --- UPDATED TO USE VARIABLE ---
    if not os.path.exists(YOUTUBE_FILE): return []
    try:
        with open(YOUTUBE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
        current_title, current_logo = "", ""
        for line in file_lines:
            line = line.strip()
            if not line: continue
            if line.lower().startswith("title"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_title = parts[1].strip()
            elif line.lower().startswith("logo"):
                parts = line.split(":", 1)
                if len(parts) > 1: current_logo = parts[1].strip()
            elif line.lower().startswith("link") or line.startswith("http"):
                url = line
                if line.lower().startswith("link"):
                    parts = line.split(":", 1)
                    if len(parts) > 1: url = parts[1].strip()
                if url.startswith("http") or url.startswith("rtmp"):
                    if not current_title: current_title = "Temporary Channel"
                    if not current_logo or len(current_logo) < 5:
                        current_logo = get_auto_logo(current_title)
                    lines.append(f'#EXTINF:-1 group-title="Temporary Channels" tvg-logo="{current_logo}",{current_title}')
                    if "http" in url and "|" not in url: url += f"|User-Agent={UA_HEADER}"
                    lines.append(url)
                    current_title, current_logo = "", ""
    except: pass
    return lines

# === MPD TXT PARSER ===
def parse_mpd_txt():
    lines = []
    # --- UPDATED TO USE VARIABLE ---
    if not os.path.exists(MPD_FILE): return []
    try:
        print(f"📥 Reading local file: {MPD_FILE}")
        with open(MPD_FILE, "r", encoding="utf-8", errors="ignore") as f:
            file_lines = f.readlines()
        
        for line in file_lines:
            line = line.strip()
            if not line: continue
            lines.append(line)
    except Exception as e:
        print(f"⚠️ Error reading {MPD_FILE}: {e}")
    return lines

def main():
    print("📥 Downloading Source Playlists...")
    ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    final_lines = ["#EXTM3U"]
    final_lines.append(f"# Last Updated: {ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}")
    final_lines.append("http://0.0.0.0")

    # --- COMBINE POCKET + ZEE JOKER ---
    source_lines = []
    source_lines.extend(fetch_raw_lines(POCKET_URL))
    source_lines.extend(fetch_raw_lines(ZEE_JOKER_URL))

    if not source_lines:
        print("❌ No data found in sources.")
        sys.exit(1)

    hd_channels_exist = set()
    for line in source_lines:
        if line.startswith("#EXTINF"):
            _, name = get_group_and_name(line)
            if "hd" in name.lower():
                hd_channels_exist.add(get_clean_id(name))

    seen_channels = set()
    current_buffer = []
    zee_tamil_count = 0

    for line in source_lines:
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTM3U"): continue

        if line.startswith("#EXTINF"):
            if current_buffer:
                final_lines.extend(current_buffer)
            current_buffer = []

            group, name = get_group_and_name(line)
            clean_name = name.lower().strip()
            
            if not should_keep_channel(group, name):
                current_buffer = [] 
                continue

            if "hd" not in clean_name:
                base_id = get_clean_id(name)
                if base_id in hd_channels_exist:
                    current_buffer = []
                    continue

            exact_clean_id = re.sub(r'[^a-z0-9]', '', clean_name)
            is_duplicate = False
            if exact_clean_id in seen_channels:
                is_duplicate = True
            else:
                seen_channels.add(exact_clean_id)

            new_group = group 
            
            if "zee tamil hd" in clean_name:
                zee_tamil_count += 1
                if zee_tamil_count == 1:
                    new_group = "Backup"
                    is_duplicate = True
                elif zee_tamil_count == 2:
                    new_group = "Tamil HD"
                    is_duplicate = False
                else:
                    new_group = "Backup"
            elif is_duplicate:
                new_group = "Backup"
            else:
                group_lower = group.lower()
                if group_lower == "tamil": new_group = "Tamil Extra"
                if "premium 24/7" in group_lower: new_group = "Tamil Extra"
                if "astro go" in group_lower: new_group = "Tamil Extra"
                if group_lower == "sports": new_group = "Sports Extra"
                if "entertainment" in group_lower: new_group = "Others"
                if "music" in group_lower: new_group = "Others"
                
                if "zee movie" in group_lower: new_group = "Others"
                elif "movies" in group_lower: new_group = "Others"
                
                if "infotainment" in group_lower: new_group = "Infotainment HD"

                if "news" in group_lower and "tamil" not in group_lower and "malayalam" not in group_lower:
                    new_group = "English and Hindi News"

                if new_group == "Tamil Extra" and "sports" in clean_name:
                    new_group = "Sports Extra"
                if "j movies" in clean_name or "raj digital plus" in clean_name: 
                    new_group = "Tamil Extra"
                if "rasi movies" in clean_name or "rasi hollywood" in clean_name: new_group = "Tamil Extra"
                if "dd sports" in clean_name: new_group = "Sports Extra"
                if any(target.lower() in clean_name for target in MOVE_TO_INFOTAINMENT_SD):
                     new_group = "Infotainment SD"
                if any(k in clean_name for k in INFOTAINMENT_KEYWORDS):
                    if "hd" not in clean_name: new_group = "Infotainment SD"
                for target in SPORTS_HD_KEEP:
                    if target.lower() in clean_name: new_group = "Sports HD"; break
                if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_NEWS]):
                    new_group = "Tamil News"
                if any(target.lower() == clean_name for target in [x.lower() for x in MOVE_TO_TAMIL_HD]): 
                    new_group = "Tamil HD"

            if new_group != group:
                if 'group-title="' in line:
                    line = re.sub(r'group-title="([^"]*)"', f'group-title="{new_group}"', line)
                else:
                    line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"')

        current_buffer.append(line)

        if not line.startswith("#"):
            current_buffer[-1] = line
            final_lines.extend(current_buffer)
            current_buffer = []

    if current_buffer:
        final_lines.extend(current_buffer)

    print("📥 Adding Live Events...")
    final_lines.extend(fetch_jio_hotstar_live())
    final_lines.extend(fetch_live_events(FANCODE_URL, "Live Events"))
    final_lines.extend(fetch_live_events(SONY_LIVE_URL, "Live Events"))
    final_lines.extend(fetch_live_events(ZEE_LIVE_URL, "Live Events"))
    print("📥 Adding JioHotstar Worker...")
    final_lines.extend(fetch_live_events(JIO_WORKER_URL, "Jio Live"))
    print("📥 Adding YouTube Live...")
    final_lines.extend(fetch_live_events(YOUTUBE_LIVE_URL, "YouTube Live"))
    final_lines.extend(parse_youtube_txt())
    
    # === ADD MANUAL MPD CHANNELS ===
    final_lines.extend(parse_mpd_txt())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))
    
    print(f"\n✅ DONE. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
