import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

proc = subprocess.Popen(['python main.py'], shell=True)

def termProc():
    proc.terminate()
    
def restartProc():
    termProc()
    proc = subprocess.Popen(['python main.py'], shell=True)

class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.src_path == '.':
            return

    def on_created(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"[*] File creation detected ({event.src_path})\n[^] Restarting...")
            restartProc()

    def on_deleted(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"[*] File deletion detected ({event.src_path})\n[^] Restarting...")
            restartProc()

    def on_modified(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"[*] File change detected ({event.src_path})\n[^] Restarting...")
            restartProc()

    def on_moved(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"[*] File move detected ({event.src_path})\n[^] Restarting...")
            restartProc()

if __name__ == "__main__":
    print("[^] Starting process.")
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n[.] Stopping process...")
        termProc()
        observer.stop()
        exit(0)
    observer.join()