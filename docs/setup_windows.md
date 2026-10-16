# Windows Development Setup

The tools this project needs on Windows, how they were installed, and fixes for problems hit along the way.

## Tools

| Tool | Purpose | Install | Check |
|---|---|---|---|
| VS Code | Editor/IDE | code.visualstudio.com (tick "Add to PATH") | `code --version` |
| Python 3.15 | Runs the project code | python.org (tick "Add python.exe to PATH") | `python --version` → 3.15.0 |
| Git | Version control | git-scm.com or `winget install -e --id Git.Git` | `git --version` |
| Docker Desktop (AMD64) | Runs PostgreSQL in a container | docker.com | `docker run hello-world` |

Recommended VS Code extensions: Python, Pylance, Container Tools, and PostgreSQL (or SQLTools).

Git identity (one time). Using GitHub's private noreply email keeps your personal email out of public commit history:
```
git config --global user.name "Your Name"
git config --global user.email "<id>+<username>@users.noreply.github.com"
```

## Python virtual environment (`.venv`)

A virtual environment is a private copy of Python for this project, holding only its libraries. It's git-ignored,
so you recreate it on each computer. From the project folder:
```
python -m venv .venv
.venv\Scripts\activate                    # prompt now starts with (.venv)
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python -c "import requests, bs4, lxml, psycopg, dotenv, pytest; print('All good!')"
```
Activate it again (`.venv\Scripts\activate`) every time you open a new terminal. VS Code usually does this
automatically once the environment is selected (Ctrl+Shift+P → "Python: Select Interpreter" → `.venv`).

Verified working on 2026-10-10 with Python 3.15.0.

## Troubleshooting log

### Python installer flagged as a threat
Download only from python.org and check that the file is signed by "Python Software Foundation"
(Properties → Digital Signatures). `winget install -e --id Python.Python.3.xx` is an alternative.

### "running scripts is disabled on this system" when activating `.venv`
PowerShell blocks scripts by default. Allow locally created scripts for your user (one time):
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Can't find the project in File Explorer
File Explorer's **Documents** shortcut may open `OneDrive\Documents`. The project is in
`C:\Users\coryh\Documents\fantasy-football-data-platform`. Paste that path into the address bar, then pin the folder to
Quick access.

### `git` not recognized after installing
Close and reopen every terminal, including VS Code's. If that doesn't help, install with winget.

### Docker: `failed to connect to the docker API at npipe:////./pipe/docker_engine`
The Docker engine isn't running. Open Docker Desktop and wait for "Engine running."

### Docker: "Virtual Machine Platform not enabled" / "No virtualization available"
These steps fixed it on this machine:
1. Check that "Intel Virtualization Technology" is enabled in the BIOS/UEFI. It already was.
2. In admin PowerShell:
   ```
   Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart
   ```
3. Verify the Windows side:
   - `Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform` should show `Enabled`.
   - `bcdedit /enum | findstr hypervisorlaunchtype` should show `Auto`.
   - `systeminfo` should report "A hypervisor has been detected."
4. Run `wsl --update`, then `wsl --shutdown`.
5. Restart the computer and reopen Docker Desktop. **This is what finally fixed it.** Docker had kept a stale failed check.

## Git & GitHub

### First-time push (how this repo was published)
1. On github.com, create an **empty** repo with no README, .gitignore or license:
   `fantasy-football-data-platform` (Public).
2. In VS Code, open the project folder (**File → Open Folder**). Check that the terminal prompt ends in
   `fantasy-football-data-platform>`.
3. Run:
   ```
   git init -b main
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/datanerdcory238/fantasy-football-data-platform.git
   git push -u origin main
   ```
4. When the sign-in window appears, choose **Sign in with your browser**. Windows remembers the sign-in.

### Everyday workflow
```
git status                 # what changed?
git add .                  # stage changes
git commit -m "message"    # save a snapshot
git push                   # upload to GitHub
```
VS Code's **Source Control** panel (Ctrl+Shift+G) does the same thing with buttons: + = add, ✓ Commit = commit,
Sync/Push = push.

### Replicating on a new computer
Install the tools above, then:
```
cd $HOME\Documents
git clone https://github.com/datanerdcory238/fantasy-football-data-platform.git
cd fantasy-football-data-platform
```
Then follow the **Quick start** in the README to set up the Python environment, `.env`, database and first data load.
`.env`, `.venv\` and `data\raw\` are not in GitHub on purpose (git-ignored), so they're recreated by those steps.

### Mistake to avoid: running Git in the wrong folder
Running `git init` / `git add .` in your **home folder** (`C:\Users\<you>`) instead of the project folder makes Git try
to track your whole user profile (AppData, Downloads and so on). It fails with many "Permission denied" warnings. Fix:
```
cd $HOME
Remove-Item -Recurse -Force .git
Remove-Item -Recurse -Force .github
```
Then open the project folder and start again. Always check the terminal prompt before running Git commands.

## Terminology
- **Terminal:** the window you type in (Windows Terminal, VS Code terminal).
- **Shell:** the program that runs your commands (PowerShell, Command Prompt, Bash). This project's commands are written for PowerShell.
- **Text editor vs IDE:** an editor edits files. An IDE adds a terminal, debugger, Git, and testing tools. VS Code is an editor that becomes IDE-like with extensions.
