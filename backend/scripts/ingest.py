import os
import sys
import httpx
import asyncio
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

console = Console()

async def ingest_files(files, api_key, host):
    url = f"{host}/api/v1/ingest"
    headers = {"asila-api-key": api_key}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Ingesting files...", total=len(files))
        
        async with httpx.AsyncClient() as client:
            for file_path in files:
                if not os.path.exists(file_path):
                    console.print(f"[yellow]Warning: File {file_path} not found, skipping.")
                    progress.advance(task)
                    continue
                    
                file_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    
                files_payload = {
                    "file": (file_name, file_content)
                }
                data_payload = {
                    "title": file_name,
                }
                
                try:
                    response = await client.post(
                        url, 
                        headers=headers, 
                        data=data_payload, 
                        files=files_payload,
                        timeout=60.0
                    )
                    
                    if response.status_code == 200:
                        pass # success
                    else:
                        console.print(f"[red]Error uploading {file_name}: {response.text}")
                except Exception as e:
                    console.print(f"[red]Error uploading {file_name}: {str(e)}")
                    
                progress.advance(task)

    console.print(f"[green]Successfully queued {len(files)} files for ingestion!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python ingest.py <file1> <file2> ...")
        sys.exit(1)
        
    api_key = os.environ.get("ASILA_API_KEY")
    if not api_key:
        console.print("[red]Error: ASILA_API_KEY environment variable is required.")
        sys.exit(1)
        
    host = os.environ.get("ASILA_HOST", "http://localhost:8000")
    
    files_to_ingest = sys.argv[1:]
    asyncio.run(ingest_files(files_to_ingest, api_key, host))
