import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "model_name": "base.en",
    "device": "cpu",
    "compute_type": "int8",
    "groq_api_key": "",
    "paste_mode": "instant_paste",  # Automatically inserts text directly into the target box
    "global_hotkey": "ctrl+alt+space",
    "sound_effects": False,
    "window_x": None,
    "window_y": None,
    "input_device_index": None,
    "auto_show_on_textbox": True
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
