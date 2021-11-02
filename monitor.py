import subprocess
import os
import platform
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

proc = "N/A"

if platform.system() == "Windows":
    proc = subprocess.Popen(['python', './main.py'], shell=True)
else:
    proc = subprocess.Popen('python ./main.py', shell=True)
    
def startProc():
    if platform.system() == "Windows":
        proc = subprocess.Popen(['python', './main.py'], shell=True)
    else:
        proc = subprocess.Popen('python ./main.py', shell=True)

def termProc():
    proc.terminate()
    
def restartProc():
    print(f"{bcolors.FAIL}[!] Terminating old process...{bcolors.ENDC}")
    termProc()
    print(f"{bcolors.OKGREEN}[^] Starting new process...{bcolors.ENDC}")
    startProc()

class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.src_path == '.':
            return

    def on_created(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[*] File creation detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

    def on_deleted(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[*] File deletion detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

    def on_modified(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[*] File change detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

    def on_moved(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[*] File move detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

if __name__ == "__main__":
    print(f"{bcolors.OKGREEN}[^] Starting process...{bcolors.ENDC}")
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print(f"\n{bcolors.FAIL}[!] Stopping process...{bcolors.ENDC}")
        termProc()
        observer.stop()
        exit(0)
    observer.join()