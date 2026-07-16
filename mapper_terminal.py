import os
from core.client import fetch_miruro_pipe
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from helper import (
    add_to_persistent_queue,
    clean_duplicate_tasks,
    episodes_mapper,
    extract_id,
    extract_m3u8_links,
    get_anime_data,
    launch_batch_worker,
    launch_batch_worker_file,
    stream_in_vlc,
)
import downloader
import sys
from core.config import MIRURO_BASE_URL

console = Console()
LANGS = ["sub", "dub"]

BANNER = """
[bold magenta]
  __  __ _                             _____  _      
 |  \/  (_)                           |  __ \| |     
 | \  / |_ _ __ _   _ _ __ ___        | |  | | |     
 | |\/| | | '__| | | | '__/ _ \       | |  | | |     
 | |  | | | |  | |_| | | | (_) |      | |__| | |____ 
 |_|  |_|_|_|   \__,_|_|  \___/       |_____/|______|
[/][bold cyan]          >> High-Performance Anime Scraper <<          [/]
"""

def header_panel(details):
    console.print(Panel(
        f"[bold white]ID:[/] {details['id']} | [bold white]TOTAL EPS:[/] {details['count']} | [bold white]TITLE: [/] {details['title']}", 
        title=f"[bold cyan]{details['title']}[/]", 
        border_style="magenta"
    ))

def mapper(result=None):
    if not result:
        link = console.input("[bold yellow]Enter Miruro Link:[/] ").strip()
        if not link: return
    
        anime_id = extract_id(link)
        
        with console.status("[bold green]Infiltrating API...") as status:
            result = get_anime_data(anime_id)
    
        if not result:
            console.print("[bold red]ERROR:[/] Connection failed.")
            return

    header_panel(result)
    
    providers = result.get("providers", {})
    master_data = episodes_mapper(providers, LANGS)

    table = Table(
        title="[bold grey50]EPISODE SELECTION MATRIX[/]", 
        show_lines=True, 
        header_style="bold cyan"
    )
    
    table.add_column("EP", justify="center", style="bold magenta")
    table.add_column("SUB", justify="left")
    table.add_column("DUB", justify="left")
    table.add_column("TITLE", style="italic green", ratio=2)
    table.add_column("DUR", justify="right", style="dim")

    for num in sorted(master_data.keys()):
        ep = master_data[num]
        
        sub_list = ", ".join(ep['avail']['sub']) if ep['avail']['sub'] else "[red]-[ /]"
        dub_list = ", ".join(ep['avail']['dub']) if ep['avail']['dub'] else "[red]-[ /]"

        table.add_row(
            str(num),
            sub_list,
            dub_list,
            ep['title'],
            ep['duration']
        )

    console.print(table)

def downloader():
    global download_path
    link = console.input("[bold yellow]Enter Miruro Link:[/] ").strip()
    if not link: return
    
    anime_id = extract_id(link)
    
    with console.status("[bold green]Infiltrating API...") as status:
        result = get_anime_data(anime_id)
    
    if not result:
        console.print("[bold red]ERROR:[/] Connection failed.")
        return
    
    mapper(result)
    
    providers = result.get("providers", {})
    master_data = episodes_mapper(providers, LANGS)
    
    try:
        choice = console.input("\n[bold yellow]Format: [EP/all] [LANG] [PROV]: [/]")
        ep_input, lang, prov = choice.split()

        safe_title = "".join([c for c in result["title"] if c not in r'<>:"/\|?*']).strip()
        
        download_path_anime = os.path.join(download_path, safe_title)
        os.makedirs(download_path_anime, exist_ok=True)
        
        queue = []
        
        target_eps = master_data.keys() if ep_input.lower() == "all" else [int(ep_input)]
        with console.status("[bold green]Infiltrating API...") as status:
            for ep_num in sorted(target_eps):
                if prov in master_data[ep_num]["avail"].get(lang, {}):
                    selected_id = master_data[ep_num]["avail"][lang][prov]
                    stream_data = extract_m3u8_links(selected_id, prov, lang)
                    streams = stream_data.get("streams", [])
                    
                    if streams:
                        queue.append({
                            "url": streams[0]["url"],
                            "ep_num": str(ep_num),
                            "download_path": download_path_anime,
                            "referer": streams[0]["referer"],
                            "origin": MIRURO_BASE_URL,
                            "anime_title": result["title"]
                        })

        if queue:
            choice = console.input("\n[bold cyan][D]ownload Now or [A]dd to episodes.json? (d/a): [/]").strip().lower()
            
            if choice == 'a':
                add_to_persistent_queue(queue)
                console.print(f"[bold green]✔ Added {len(queue)} tasks to episodes.json![/]")
            else:
                console.print(f"[bold green]✔ Starting batch download for {len(queue)} episodes...[/]")
                launch_batch_worker(queue)
        else:
            console.print("[bold red]No valid streams found for selection.[/]")

    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/] {e}")    

def streamer():
    link = console.input("[bold yellow]Enter Miruro Link:[/] ").strip()
    if not link: return

    anime_id = extract_id(link)

    with console.status("[bold green]Infiltrating API...") as status:
        result = get_anime_data(anime_id)

    if not result:
        console.print("[bold red]ERROR:[/] Connection failed.")
        return

    mapper(result)

    providers = result.get("providers", {})
    master_data = episodes_mapper(providers, LANGS)

    try:
        choice = console.input("\n[bold yellow]Enter selection to Stream [EP] [LANG] [PROV]: [/]")
        ep_input, lang, prov = choice.split()
        ep_num = int(ep_input)

        if ep_num not in master_data:
            console.print(f"[bold red]Episode {ep_num} was not found.[/]")
            return

        if prov not in master_data[ep_num]["avail"].get(lang, {}):
            console.print(f"[bold red]No {lang} stream found for episode {ep_num} on provider '{prov}'.[/]")
            return

        selected_id = master_data[ep_num]["avail"][lang][prov]

        with console.status("[bold green]Extracting stream...") as status:
            stream_data = extract_m3u8_links(selected_id, prov, lang)

        streams = stream_data.get("streams", [])
        if not streams:
            console.print("[bold red]No valid streams found for selection.[/]")
            return

        stream_url = streams[0]["url"]
        referer_url = streams[0]["referer"]
        anime_title = result["title"]
        started = stream_in_vlc(stream_url, referer_url, f"{anime_title} - Ep {ep_num}")

        if started:
            console.print(f"[bold green]✔ Streaming episode {ep_num} in VLC...[/]")
        else:
            console.print("[bold red]VLC was not found. Please install VLC or add it to your PATH.[/]")

    except ValueError:
        console.print("[bold red]Invalid format. Use: [EP] [LANG] [PROV], for example: 1 sub kiwi[/]")
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/] {e}")    

if __name__ == "__main__":
    download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Anime")
    os.makedirs(download_path, exist_ok=True)
    console.clear()
    while True:
        try:
            rprint(BANNER)
            rprint("[bold white]Main Menu:[/]")
            rprint(" [1] [cyan]Map Anime[/]")
            rprint(" [2] [green]Add/Download Anime[/]")
            rprint(" [3] [magenta]Start Queue (episodes.json)[/]")
            rprint(" [4] [blue]Stream Anime (VLC)[/]")
            rprint(" [0] [red]Exit[/]")
            
            choice = console.input("\n[bold yellow]Select Option: [/]").strip()

            if choice == "1":
                console.clear()
                rprint(BANNER)
                mapper()
            elif choice == "2":
                console.clear()
                rprint(BANNER)
                downloader()
            elif choice == "3":
                if os.path.exists("download_queue.json"):
                    clean_duplicate_tasks("download_queue.json")
                    launch_batch_worker_file("download_queue.json")
                else:
                    rprint("[bold red]No download_queue.json found![/]")
            elif choice == "4":
                console.clear()
                rprint(BANNER)
                streamer()
            elif choice == "0":
                break
        except KeyboardInterrupt:
            break
