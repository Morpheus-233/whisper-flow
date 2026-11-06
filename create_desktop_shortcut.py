import os
import sys
import subprocess

def create_shortcut(target_exe=None):
    """
    Creates or updates the Desktop and Start Menu shortcuts to Whisper Flow,
    and registers App Paths so Windows Search, Run dialog, and launcher apps
    can find and launch WhisperFlow anywhere.
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Whisper Flow.lnk")
    
    start_menu = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Microsoft", "Windows", "Start Menu", "Programs")
    start_shortcut_path = os.path.join(start_menu, "Whisper Flow.lnk")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if target_exe is None:
        default_app = os.path.join(current_dir, "WhisperFlow_App", "WhisperFlow.exe")
        if os.path.exists(default_app):
            target_exe = default_app

    if target_exe and os.path.exists(target_exe):
        target_path = os.path.abspath(target_exe)
        working_dir = os.path.dirname(target_path)
        arguments = ""
        app_ico = os.path.join(working_dir, "assets", "icon.ico")
        if not os.path.exists(app_ico):
            app_ico = os.path.join(current_dir, "assets", "icon.ico")
        if os.path.exists(app_ico):
            icon_location = f"{app_ico},0"
        else:
            icon_location = f"{target_path},0"
    else:
        vbs_path = os.path.join(current_dir, "WhisperFlow_Silent.vbs")
        target_path = "wscript.exe"
        working_dir = current_dir
        arguments = f'"{vbs_path}"'
        icon_location = "C:\\Windows\\System32\\wscript.exe,0"

    for sc_path in [shortcut_path, start_shortcut_path]:
        if os.path.exists(sc_path):
            try:
                os.remove(sc_path)
            except Exception:
                pass

    os.makedirs(start_menu, exist_ok=True)

    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell

# 1. Desktop shortcut
$Shortcut1 = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut1.TargetPath = '{target_path}'
$Shortcut1.Arguments = '{arguments}'
$Shortcut1.WorkingDirectory = '{working_dir}'
$Shortcut1.IconLocation = '{icon_location}'
$Shortcut1.Description = 'Launch Whisper Flow Dictation'
$Shortcut1.Save()

# 2. Start Menu shortcut (for Windows Search and Start Menu apps)
$Shortcut2 = $WshShell.CreateShortcut('{start_shortcut_path}')
$Shortcut2.TargetPath = '{target_path}'
$Shortcut2.Arguments = '{arguments}'
$Shortcut2.WorkingDirectory = '{working_dir}'
$Shortcut2.IconLocation = '{icon_location}'
$Shortcut2.Description = 'Launch Whisper Flow Dictation'
$Shortcut2.Save()

# 3. App Paths registration (for Win+R, launcher apps, Windows Search)
$appPaths = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths"
try {{
    if (-not (Test-Path "$appPaths\\WhisperFlow.exe")) {{
        New-Item -Path "$appPaths\\WhisperFlow.exe" -Force | Out-Null
    }}
    Set-ItemProperty -Path "$appPaths\\WhisperFlow.exe" -Name "(Default)" -Value '{target_path}'
    Set-ItemProperty -Path "$appPaths\\WhisperFlow.exe" -Name "Path" -Value '{working_dir}'

    if (-not (Test-Path "$appPaths\\Whisper Flow.exe")) {{
        New-Item -Path "$appPaths\\Whisper Flow.exe" -Force | Out-Null
    }}
    Set-ItemProperty -Path "$appPaths\\Whisper Flow.exe" -Name "(Default)" -Value '{target_path}'
    Set-ItemProperty -Path "$appPaths\\Whisper Flow.exe" -Name "Path" -Value '{working_dir}'
}} catch {{}}

# 4. User PATH addition if not present
try {{
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -split ';' -notcontains '{working_dir}') {{
        [Environment]::SetEnvironmentVariable("Path", "$userPath;{working_dir}", "User")
    }}
}} catch {{}}
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully created desktop shortcut at: {shortcut_path}")
        print(f"Successfully created start menu shortcut at: {start_shortcut_path}")
        print(f"Registered App Paths for: {target_path}")
        return True
    else:
        print(f"Error creating shortcut: {res.stderr}")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    create_shortcut(target)
