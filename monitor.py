import subprocess, sys, platform, psutil, os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

if '--no-color' in sys.argv:
    class bcolors:
        HEADER = ''
        OKBLUE = ''
        OKCYAN = ''
        OKGREEN = ''
        WARNING = ''
        FAIL = ''
        ENDC = ''
        BOLD = ''
        UNDERLINE = ''
else:
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
        
global proc, pidlist
pidlist = []

def kill():
    global pidlist
    for proc in psutil.process_iter():
        if proc.pid in pidlist:
            print(f"{bcolors.FAIL}[monitor] Terminating old process...{bcolors.ENDC}")
            process = psutil.Process(proc.pid)
            for proc in process.children(recursive=True):
                proc.terminate()
            process.kill()
            print(proc.status())

def startProc():
    global proc, pidlist
    if platform.system() == "Windows":
        proc = subprocess.Popen(['python', './main.py'], shell=True)
    else:
        proc = subprocess.Popen('python ./main.py', shell=True)
    pidlist.append(proc.pid)

def restartProc():
    kill()
    print(f"{bcolors.OKGREEN}[monitor] Starting new process...{bcolors.ENDC}")
    startProc()

class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.src_path == '.':
            return

    def on_created(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[monitor] File creation detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

    def on_deleted(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[monitor] File deletion detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

    def on_modified(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[monitor] File change detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

    def on_moved(self, event):
        if event.src_path == '.':
            return
        if event.src_path.endswith('.py') | event.src_path.endswith('.json'):
            print(f"{bcolors.OKGREEN}[monitor] File move detected ({bcolors.ENDC}{bcolors.UNDERLINE}{event.src_path}{bcolors.ENDC}{bcolors.OKGREEN})\n[^] Restarting...{bcolors.ENDC}")
            restartProc()

if __name__ == "__main__":
    print(f"{bcolors.OKGREEN}[monitor] Starting process...{bcolors.ENDC}")
    startProc()
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print(f"\n{bcolors.FAIL}[monitor] Stopping process...{bcolors.ENDC}")
        kill()
        observer.stop()
        exit(0)
    observer.join()