import subprocess, sys, os

os.chdir("D:/Programs/fastapi/aipaneladmin")
PYTHON = "d:/Programs/py312env/Scripts/python.exe"

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

proc = subprocess.Popen(
    [PYTHON, "run.py"],
    stdout=open("D:/Programs/fastapi/aipaneladmin/server_stdout.log", "w"),
    stderr=open("D:/Programs/fastapi/aipaneladmin/server_stderr.log", "w"),
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
    close_fds=True,
)

with open("D:/Programs/fastapi/aipaneladmin/server.pid", "w") as f:
    f.write(str(proc.pid))

print(f"Server PID: {proc.pid}")