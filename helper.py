from core.client import fetch_miruro_pipe
from datetime import timedelta
import subprocess
import tempfile
import json
import os
import platform
import shutil

def extract_id(link):
    if "watch/" in link:
        link = link.split("watch/")[-1]
    slash_index = link.find("/")
    return link[:slash_index] if slash_index != -1 else link

def get_anime_data(id):
    params = {"anilistId": id}
    result = fetch_miruro_pipe("episodes", "GET", params)

    if result.get("type") == "json":
        data = result.get("data", {})
        mappings = data.get("mappings", {})
        return {
            "id": id,
            "title": mappings.get("title", "Unknown"),
            "count": mappings.get("episodes", "?"),
            "providers": data.get("providers", {})
        }
    return None

def episodes_mapper(providers, LANGS):
    master_data = {} 

    for p_name, p_content in providers.items():
        episodes_raw = p_content.get("episodes", {})
        
        for lang in LANGS:
            for ep in episodes_raw.get(lang, []):
                num = ep.get("number", 0)
                
                if num not in master_data:
                    raw_dur = ep.get("duration", 0)
                    master_data[num] = {
                        "title": ep.get("title", "UNKNOWN"),
                        "duration": str(timedelta(seconds=int(raw_dur))),
                        "avail": {l: {} for l in LANGS} 
                    }
                
                master_data[num]["avail"][lang][p_name] = ep.get("id")
    
    return master_data

def extract_m3u8_links(id, provider, lang):
    params = {"episodeId": id, "provider": provider, "category": lang}
    result = fetch_miruro_pipe("sources", "GET", params)
    
    if result.get("type") != "json":
        return {"streams": []}
    
    data = result.get("data", {})
    streams_list = []

    if isinstance(data, dict):
        if "sub" in data and isinstance(data["sub"], dict):
            streams_list = data["sub"].get("streams", [])
        elif "dub" in data and isinstance(data["dub"], dict):
            streams_list = data["dub"].get("streams", [])
        elif "ssub" in data and isinstance(data["ssub"], dict):
            streams_list = data["ssub"].get("streams", [])
        else:
            streams_list = data.get("streams", [])
    elif isinstance(data, list):
        streams_list = data

    if not isinstance(streams_list, list):
        streams_list = []

    m3u8_links = {
        "streams": [
            {"url": s.get("url"), "referer": s.get("referer")} 
            for s in streams_list 
            if isinstance(s, dict) and s.get("url", "").endswith(".m3u8")
        ]
    }
    print(f"Extracted {len(m3u8_links['streams'])} m3u8 links for episode ID {id} from provider '{provider}' in language '{lang}'.")
    return m3u8_links

def get_vlc_path():
    system = platform.system()

    if system == "Windows":
        registry_paths = [
            (r"SOFTWARE\VideoLAN\VLC", "InstallDir"),
            (r"SOFTWARE\WOW6432Node\VideoLAN\VLC", "InstallDir"),
        ]

        try:
            import winreg

            for registry_path, value_name in registry_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                        install_dir, _ = winreg.QueryValueEx(key, value_name)
                        vlc_path = os.path.join(install_dir, "vlc.exe")
                        if os.path.exists(vlc_path):
                            return vlc_path
                except OSError:
                    pass
        except ImportError:
            pass

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        candidates = [
            os.path.join(program_files, "VideoLAN", "VLC", "vlc.exe"),
            os.path.join(program_files_x86, "VideoLAN", "VLC", "vlc.exe"),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        return shutil.which("vlc") or shutil.which("vlc.exe")

    if system == "Darwin":
        vlc_path = "/Applications/VLC.app/Contents/MacOS/VLC"
        if os.path.exists(vlc_path):
            return vlc_path
        return shutil.which("vlc")

    if system == "Linux":
        return shutil.which("vlc") or "vlc"

    return shutil.which("vlc")

def stream_in_vlc(stream_url, referer_url, title="Anime Stream"):
    vlc_path = get_vlc_path()
    if not vlc_path:
        return False

    command = [
        vlc_path,
        stream_url,
        f":http-referrer={referer_url}",
        f"--meta-title={title}",
        "--network-caching=1500"
    ]

    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def add_to_persistent_queue(task_list, filename="download_queue.json"):
    existing_tasks = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_tasks = json.load(f)
        except:
            existing_tasks = []

    existing_tasks.extend(task_list)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_tasks, f, indent=4)

def launch_batch_worker(task_list):
    downloader_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloader.py")
    wt_alias = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        json.dump(task_list, tf)
        temp_file_path = tf.name

    command = f'"{wt_alias}" -p "Command Prompt" --title "Cipher Engine" python "{downloader_path}" "{temp_file_path}"'
    subprocess.Popen(command, shell=True)

def launch_batch_worker_file(file_path):
    downloader_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloader.py")
    wt_alias = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe')
    
    command = f'"{wt_alias}" -p "Command Prompt" --title "Cipher Engine" python "{downloader_path}" "{os.path.abspath(file_path)}"'
    subprocess.Popen(command, shell=True)

def clean_duplicate_tasks(filename="download_queue.json"):
    """Removes duplicate tasks based on the unique m3u8 URL."""
    if not os.path.exists(filename):
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        unique_tasks = []
        seen_urls = set()

        for task in tasks:
            url = task.get('url')
            if url not in seen_urls:
                unique_tasks.append(task)
                seen_urls.add(url)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(unique_tasks, f, indent=4)
        
            
    except Exception as e:
        print(f"Error cleaning duplicates: {e}")
