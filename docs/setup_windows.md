# Windows Development Setup

The tools this project needs on Windows, how they were installed, and fixes for problems hit along the way.

## Tools

| Tool | Purpose | Install | Check |
|---|---|---|---|
| VS Code | Editor/IDE | code.visualstudio.com (tick "Add to PATH") | `code --version` |
| Python 3.15 | Runs the project code | python.org (tick "Add python.exe to PATH") | `python --version` |
| Git | Version control | git-scm.com or `winget install -e --id Git.Git` | `git --version` |
| Docker Desktop (AMD64) | Runs PostgreSQL in a container | docker.com | `docker run hello-world` |

Recommended VS Code extensions: Python, Pylance, Container Tools, and PostgreSQL (or SQLTools).

Git identity (one time). Using GitHub's private noreply email keeps your personal email out of public commit history:
```
git config --global user.name "Your Name"
git config --global user.email "<id>+<username>@users.noreply.github.com"
```

## Troubleshooting log

### Python installer flagged as a threat
Download only from python.org and check that the file is signed by "Python Software Foundation"
(Properties → Digital Signatures). `winget install -e --id Python.Python.3.xx` is an alternative.

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

## Terminology
- **Terminal:** the window you type in (Windows Terminal, VS Code terminal).
- **Shell:** the program that runs your commands (PowerShell, Command Prompt, Bash). This project's commands are written for PowerShell.
- **Text editor vs IDE:** an editor edits files. An IDE adds a terminal, debugger, Git, and testing tools. VS Code is an editor that becomes IDE-like with extensions.
