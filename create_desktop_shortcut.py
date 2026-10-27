import os
import sys
import subprocess

def create_shortcut(target_exe=None):
    """
    Creates or updates the Desktop shortcut to Whisper Flow.
    When target_exe is provided (e.g. WhisperFlow_App\\WhisperFlow.exe), points directly
    to the standalone executable without launching any console or script wrapper.
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Whisper Flow.lnk")
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if target_exe is None:
        default_app = os.path.join(current_dir, "WhisperFlow_App", "WhisperFlow.exe")
        if os.path.exists(default_app):
            target_exe = default_app

    if target_exe and os.path.exists(target_exe):
        target_path = os.path.abspath(target_exe)
        working_dir = os.path.dirname(target_path)
        arguments = ""
        icon_location = f"{target_path},0"
    else:
        vbs_path = os.path.join(current_dir, "WhisperFlow_Silent.vbs")
        target_path = "wscript.exe"
        working_dir = current_dir
        arguments = f'"{vbs_path}"'
        icon_location = "C:\\Windows\\System32\\wscript.exe,0"

    if os.path.exists(shortcut_path):
        try:
            os.remove(shortcut_path)
        except Exception:
            pass

    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target_path}'
$Shortcut.Arguments = '{arguments}'
$Shortcut.WorkingDirectory = '{working_dir}'
$Shortcut.IconLocation = '{icon_location}'
$Shortcut.Description = 'Launch Whisper Flow Dictation'
$Shortcut.Save()
"""
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully created desktop shortcut at: {shortcut_path}")
        return True
    else:
        print(f"Error creating shortcut: {res.stderr}")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    create_shortcut(target)
