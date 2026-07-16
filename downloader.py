import yt_dlp
import sys
import os
import json
import time
from yt_dlp.networking.impersonate import ImpersonateTarget
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn
from rich.live import Live
from rich.panel import Panel

progress = Progress(
    SpinnerColumn("dots12"),
    TextColumn("[bold magenta]{task.fields[anime]}"), 
    TextColumn("[bold blue]EP {task.fields[ep]}"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.0f}%", 
    "•",
    DownloadColumn(), 
    "•",
    TextColumn("[bold green]{task.fields[speed]}"), 
    expand=True
)

class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def create_hook(task_id):
    """Creates a unique hook for the specific episode task ID."""
    def hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            raw_speed = d.get('speed')
            speed_str = f"{yt_dlp.utils.format_bytes(raw_speed)}/s" if raw_speed else "[bold green]0.00 B/s[/]"
            
            progress.update(task_id, completed=downloaded, total=total, speed=speed_str)
            
        elif d['status'] == 'finished':
            final_bytes = d.get('total_bytes') or d.get('downloaded_bytes', 0)
            progress.update(task_id, completed=final_bytes, total=final_bytes, speed="[bold green]Finished[/]")
    return hook

def run_download(task, task_id):
    """Downloads a single episode and updates its specific bar."""
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Mode': 'navigate'
    }
    if task.get('referer'):
        headers['Referer'] = task.get('referer')
    if task.get('origin'):
        headers['Origin'] = task.get('origin')

    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'logger': SilentLogger(),
        'noprogress': True, 
        'hls_use_mpegts': True, 
        'format': 'best',
        'concurrent_fragment_downloads': 1,
        
        'http_headers': headers,
        
        'impersonate': ImpersonateTarget.from_str('chrome'), 
        'extractor_args': {
            'generic': {
                'impersonate': ['chrome']
            }
        },
        
        'check_formats': False, 
        
        'paths': {'home': task['download_path']},
        'outtmpl': {'default': f"{task['ep_num']}.%(ext)s"},
        'progress_hooks': [create_hook(task_id)],
    }

    try:
        progress.update(task_id, speed="[yellow]Starting...[/]")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([task['url']])
        return True 
    except Exception as e:
        progress.update(task_id, speed=f"[bold red]Failed[/]")
        return False 
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <task_file_path>")
        sys.exit(1)

    task_file_path = sys.argv[1]
    
    try:
        with open(task_file_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
    except Exception as e:
        print(f"Failed to load tasks: {e}")
        sys.exit(1)

    task_map = []
    for t in tasks:
        full_title = t.get('anime_title', 'Unknown')
        display_title = (full_title[:20] + '..') if len(full_title) > 22 else full_title
        
        tid = progress.add_task(
            "Queue", 
            total=None, 
            anime=display_title, 
            ep=t['ep_num'], 
            speed="[dim]Waiting...[/]"
        )
        task_map.append((t, tid))

    main_panel = Panel(
        progress, 
        title="[bold cyan]CipherDownloader v1.0 - Sequential Queue[/]", 
        border_style="blue",
        padding=(0, 1),
        expand=True
    )
    
    with Live(main_panel, refresh_per_second=50, screen=False):
        for task_data, task_id in task_map:
            success = run_download(task_data, task_id)
            time.sleep(0.5)
            
            if success:
                progress.remove_task(task_id)
