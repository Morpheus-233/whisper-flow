import json
import os
import sys

DEFAULT_CONFIG = {
    "model_name": "base",
    "device": "cpu",
    "compute_type": "int8",
    "groq_api_key": "",
    "engine_mode": "groq",  # "groq" or "local"
    "language_mode": "hinglish",  # "hinglish" or "en"
    "paste_mode": "instant_paste",  # Automatically inserts text directly into the target box
    "global_hotkey": "ctrl+shift+space",
    "sound_effects": False,
    "window_x": None,
    "window_y": None,
    "input_device_index": None,
    "auto_show_on_textbox": True
}

def get_app_data_dir():
    """Returns the dedicated WhisperFlow data directory."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "WhisperFlow")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def get_resource_path(relative_path: str) -> str:
    """Resolves bundled assets whether running in PyInstaller frozen environment or source."""
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

def get_config_path() -> str:
    """Returns the path to config.json, migrating legacy configurations if running frozen."""
    if getattr(sys, "frozen", False):
        target_path = os.path.join(get_app_data_dir(), "config.json")
        if not os.path.exists(target_path):
            exe_dir = os.path.dirname(sys.executable)
            candidate_dirs = [
                exe_dir,
                os.path.dirname(exe_dir),
                os.getcwd(),
                os.path.dirname(os.getcwd()),
                getattr(sys, "_MEIPASS", "")
            ]
            for c_dir in candidate_dirs:
                if c_dir and os.path.exists(os.path.join(c_dir, "config.json")):
                    try:
                        import shutil
                        shutil.copy2(os.path.join(c_dir, "config.json"), target_path)
                        break
                    except Exception as e:
                        print(f"Notice migrating config.json: {e}")
        return target_path
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    config_file = get_config_path()
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
    cfg = DEFAULT_CONFIG.copy()
    if getattr(sys, "frozen", False) and not os.path.exists(config_file):
        save_config(cfg)
    return cfg

def save_config(config):
    config_file = get_config_path()
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
