import subprocess
import sys
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from api.settings import BASE_DIR

venv_python = sys.executable

processes = {
    "django": [str(venv_python), "manage.py", "runserver", "0.0.0.0:8000"],
    "redis": ["redis-server"],
    "celery": [
        str(venv_python),
        "-m",
        "celery",
        "-A",
        "api",
        "worker",
        "--loglevel=info",
        "--pool=solo",
    ],
}

procs = {name: subprocess.Popen(cmd) for name, cmd in processes.items()}


class ReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            print("🔄 Restarting Celery...")
            procs["celery"].terminate()
            procs["celery"].wait()
            procs["celery"] = subprocess.Popen(processes["celery"])


observer = Observer()
observer.schedule(ReloadHandler(), str(BASE_DIR), recursive=True)
observer.start()

try:
    for p in procs.values():
        p.wait()
except KeyboardInterrupt:
    for p in procs.values():
        p.terminate()
    observer.stop()
observer.join()
