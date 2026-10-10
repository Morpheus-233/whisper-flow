import os
import subprocess

def create_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Whisper Flow.lnk")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vbs_path = os.path.join(current_dir, "WhisperFlow_Silent.vbs")

    if os.path.exists(shortcut_path):
        try:
            os.remove(shortcut_path)
        except Exception:
            pass

    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = 'wscript.exe'
$Shortcut.Arguments = '"{vbs_path}"'
$Shortcut.WorkingDirectory = '{current_dir}'
$Shortcut.IconLocation = 'C:\\Windows\\System32\\wscript.exe,0'
$Shortcut.Description = 'Launch Whisper Flow Dictation'
$Shortcut.Save()
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully recreated desktop shortcut at: {shortcut_path}")
    else:
        print(f"Error creating shortcut: {res.stderr}")

if __name__ == "__main__":
    create_shortcut()
