import os
import sys
import subprocess
import threading
import queue
import time
import shutil
import webbrowser

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_LOG_PATH = os.path.join(REPO_DIR, "build_log.txt")
BUILD_VENV_DIR = os.path.join(REPO_DIR, ".build_venv")
OUTPUT_APP_DIR = os.path.join(REPO_DIR, "WhisperFlow_App")
SPEC_PATH = os.path.join(REPO_DIR, "WhisperFlow.spec")
REQUIREMENTS_PATH = os.path.join(REPO_DIR, "requirements.txt")

def find_system_python():
    """Finds a viable Python 3.10+ command."""
    candidates = [
        ["py", "-3"],
        [sys.executable] if sys.executable else [],
        ["python"],
        ["python3"],
    ]
    for cmd in candidates:
        if not cmd:
            continue
        try:
            res = subprocess.run(
                cmd + ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                ver_str = res.stdout.strip()
                major, minor = map(int, ver_str.split(".")[:2])
                if (major, minor) >= (3, 10):
                    return cmd
        except Exception:
            continue
    return [sys.executable] if sys.executable else ["python"]

class BuildWorker:
    """Executes the standalone build steps and streams progress."""
    def __init__(self, include_gpu=False, log_callback=None, step_callback=None, done_callback=None):
        self.include_gpu = include_gpu
        self.log_callback = log_callback or (lambda msg: None)
        self.step_callback = step_callback or (lambda step, total, desc: None)
        self.done_callback = done_callback or (lambda success, err_step, log_tail: None)
        self.full_log = []
        self.is_cancelled = False

    def log(self, text):
        self.full_log.append(text)
        self.log_callback(text)

    def run_command(self, cmd, step_name):
        self.log(f"--- Running: {' '.join(cmd)} ---")
        try:
            process = subprocess.Popen(
                cmd,
                cwd=REPO_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            for line in iter(process.stdout.readline, ''):
                if self.is_cancelled:
                    process.kill()
                    return False
                self.log(line.rstrip())
            process.stdout.close()
            process.wait()
            if process.returncode != 0:
                self.log(f"Error: {step_name} exited with code {process.returncode}")
                return False
            return True
        except Exception as e:
            self.log(f"Exception during {step_name}: {e}")
            return False

    def build(self):
        start_time = time.time()
        steps = [
            ("Prepare Build Environment", self._step_create_venv),
            ("Install Dependencies", self._step_install_deps),
            ("Compile Executable with PyInstaller", self._step_run_pyinstaller),
            ("Assemble Standalone Directory", self._step_copy_output),
            ("Create Desktop Shortcut", self._step_create_shortcut),
        ]
        total_steps = len(steps)

        for i, (name, fn) in enumerate(steps, start=1):
            self.step_callback(i, total_steps, name)
            self.log(f"\n==========================================")
            self.log(f"Step {i}/{total_steps}: {name}")
            self.log(f"==========================================")
            ok = fn()
            if not ok:
                tail = "\n".join(self.full_log[-30:])
                self._save_log_file()
                self.done_callback(False, name, tail)
                return

        elapsed = time.time() - start_time
        mins, secs = divmod(int(elapsed), 60)
        size_mb = self._calc_output_size_mb()

        self.log(f"\n==========================================")
        self.log(f"Build completed successfully in {mins}m {secs}s!")
        self.log(f"Output directory: {OUTPUT_APP_DIR}")
        self.log(f"Total package size: {size_mb:.1f} MB")
        self.log(f"==========================================")
        self._save_log_file()
        self.done_callback(True, "", "")

    def _save_log_file(self):
        try:
            with open(BUILD_LOG_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(self.full_log))
        except Exception as e:
            print(f"Failed to write build log: {e}")

    def _calc_output_size_mb(self):
        total_size = 0
        if os.path.exists(OUTPUT_APP_DIR):
            for dirpath, dirnames, filenames in os.walk(OUTPUT_APP_DIR):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)

    def _get_venv_python(self):
        return os.path.join(BUILD_VENV_DIR, "Scripts", "python.exe")

    def _step_create_venv(self):
        if not os.path.exists(BUILD_VENV_DIR):
            self.log("Creating dedicated .build_venv virtual environment...")
            sys_py = find_system_python()
            return self.run_command(sys_py + ["-m", "venv", BUILD_VENV_DIR], "venv creation")
        self.log("Existing .build_venv found. Reusing virtual environment.")
        return True

    def _step_install_deps(self):
        venv_py = self._get_venv_python()
        if not os.path.exists(venv_py):
            self.log(f"Cannot find Python in build venv: {venv_py}")
            return False

        self.log("Upgrading pip in build venv...")
        self.run_command([venv_py, "-m", "pip", "install", "--upgrade", "pip"], "pip upgrade")

        self.log("Installing requirements.txt and pyinstaller...")
        ok = self.run_command([venv_py, "-m", "pip", "install", "-r", REQUIREMENTS_PATH, "pyinstaller>=6.5.0"], "install dependencies")
        if not ok:
            return False

        if self.include_gpu:
            self.log("Installing optional NVIDIA CUDA packages (nvidia-cublas-cu12, nvidia-cudnn-cu12)...")
            ok_gpu = self.run_command([venv_py, "-m", "pip", "install", "nvidia-cublas-cu12", "nvidia-cudnn-cu12"], "install cuda")
            if not ok_gpu:
                self.log("Notice: CUDA package install returned non-zero code. Local CPU mode remains fully supported.")

        return True

    def _step_run_pyinstaller(self):
        venv_py = self._get_venv_python()
        cmd = [
            venv_py,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            SPEC_PATH
        ]
        return self.run_command(cmd, "PyInstaller build")

    def _step_copy_output(self):
        dist_dir = os.path.join(REPO_DIR, "dist", "WhisperFlow")
        if not os.path.exists(dist_dir):
            self.log(f"Error: Expected build folder not found at {dist_dir}")
            return False

        self.log(f"Copying build output to {OUTPUT_APP_DIR}...")
        try:
            if os.name == 'nt':
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "WhisperFlow.exe"], capture_output=True)
                    time.sleep(0.3)
                except Exception:
                    pass
            os.makedirs(OUTPUT_APP_DIR, exist_ok=True)
            for item in os.listdir(dist_dir):
                s = os.path.join(dist_dir, item)
                d = os.path.join(OUTPUT_APP_DIR, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            return True
        except Exception as e:
            self.log(f"Error assembling standalone folder: {e}")
            return False

    def _step_create_shortcut(self):
        target_exe = os.path.join(OUTPUT_APP_DIR, "WhisperFlow.exe")
        if not os.path.exists(target_exe):
            self.log(f"Warning: WhisperFlow.exe not found at {target_exe}")
            return False

        self.log("Creating Desktop shortcut pointing to WhisperFlow.exe...")
        try:
            from create_desktop_shortcut import create_shortcut
            ok = create_shortcut(target_exe=target_exe)
            return ok
        except Exception as e:
            self.log(f"Notice creating shortcut: {e}")
            return True


# =========================================================================
# Tkinter Progress Window GUI (Zero External Dependencies)
# =========================================================================
def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("Whisper Flow Standalone Builder")
    root.geometry("780x560")
    root.minsize(640, 480)

    icon_path = os.path.join(REPO_DIR, "assets", "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    # Styling colors
    BG_DARK = "#12101a"
    CARD_BG = "#1a1626"
    ACCENT_PURPLE = "#7c3aed"
    TEXT_LIGHT = "#f8fafc"
    TEXT_MUTED = "#94a3b8"
    LOG_BG = "#0d0b14"
    BORDER_COLOR = "#2d243f"

    root.configure(bg=BG_DARK)

    # Main container
    main_frame = tk.Frame(root, bg=BG_DARK, padx=20, pady=16)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Header
    title_label = tk.Label(
        main_frame,
        text="Whisper Flow Standalone Builder",
        font=("Segoe UI", 16, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_DARK
    )
    title_label.pack(anchor="w")

    subtitle_label = tk.Label(
        main_frame,
        text="Builds a zero-console standalone executable (WhisperFlow.exe) with local and cloud transcription.",
        font=("Segoe UI", 10),
        fg=TEXT_MUTED,
        bg=BG_DARK
    )
    subtitle_label.pack(anchor="w", pady=(2, 12))

    # Options Card
    options_frame = tk.Frame(main_frame, bg=CARD_BG, padx=14, pady=10, highlightbackground=BORDER_COLOR, highlightthickness=1)
    options_frame.pack(fill=tk.X, pady=(0, 10))

    gpu_var = tk.BooleanVar(value=False)
    gpu_checkbox = tk.Checkbutton(
        options_frame,
        text="Include NVIDIA GPU support (larger build, requires installing extra packages)",
        variable=gpu_var,
        font=("Segoe UI", 10),
        fg=TEXT_LIGHT,
        bg=CARD_BG,
        activebackground=CARD_BG,
        activeforeground=TEXT_LIGHT,
        selectcolor=BG_DARK
    )
    gpu_checkbox.pack(anchor="w")

    # Status & Progress Section
    progress_frame = tk.Frame(main_frame, bg=BG_DARK)
    progress_frame.pack(fill=tk.X, pady=(0, 8))

    status_label = tk.Label(
        progress_frame,
        text="Ready. Click 'Start Build' to produce WhisperFlow.exe.",
        font=("Segoe UI", 10, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_DARK
    )
    status_label.pack(anchor="w", pady=(0, 4))

    style = ttk.Style()
    style.theme_use('default')
    style.configure(
        "Custom.Horizontal.TProgressbar",
        background=ACCENT_PURPLE,
        troughcolor=CARD_BG,
        bordercolor=BORDER_COLOR,
        lightcolor=ACCENT_PURPLE,
        darkcolor=ACCENT_PURPLE
    )

    progress_bar = ttk.Progressbar(
        progress_frame,
        style="Custom.Horizontal.TProgressbar",
        orient="horizontal",
        mode="determinate",
        maximum=100
    )
    progress_bar.pack(fill=tk.X, pady=(0, 4))

    # Log Terminal View
    log_frame = tk.Frame(main_frame, bg=LOG_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

    log_text = tk.Text(
        log_frame,
        wrap="char",
        font=("Consolas", 9),
        bg=LOG_BG,
        fg="#cbd5e1",
        insertbackground=TEXT_LIGHT,
        relief=tk.FLAT,
        padx=10,
        pady=8
    )
    scrollbar = tk.Scrollbar(log_frame, command=log_text.yview, bg=CARD_BG)
    log_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Button Bar
    button_bar = tk.Frame(main_frame, bg=BG_DARK)
    button_bar.pack(fill=tk.X)

    log_queue = queue.Queue()
    step_queue = queue.Queue()
    done_queue = queue.Queue()

    worker_ref = [None]

    def append_log_ui(msg):
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)

    def process_queues():
        while not log_queue.empty():
            try:
                msg = log_queue.get_nowait()
                append_log_ui(msg)
            except queue.Empty:
                break

        while not step_queue.empty():
            try:
                step, total, desc = step_queue.get_nowait()
                percent = int((step / total) * 100)
                progress_bar['value'] = percent
                status_label.config(text=f"Step {step}/{total}: {desc}")
            except queue.Empty:
                break

        while not done_queue.empty():
            try:
                success, err_step, log_tail = done_queue.get_nowait()
                if success:
                    status_label.config(text="Build Succeeded! WhisperFlow.exe is ready.", fg="#4ade80")
                    progress_bar['value'] = 100
                    btn_start.pack_forget()
                    btn_launch.pack(side=tk.LEFT, padx=(0, 8))
                    btn_open_folder.pack(side=tk.LEFT, padx=(0, 8))
                    btn_close.config(text="Close", state=tk.NORMAL)
                else:
                    status_label.config(text=f"Build Failed at: {err_step}", fg="#f87171")
                    append_log_ui(f"\n[BUILD FAILURE IN STEP: {err_step}]")
                    append_log_ui(f"Check build_log.txt for complete trace.\nRecent log output:\n{log_tail}")
                    btn_start.config(state=tk.NORMAL, text="Retry Build")
                    btn_view_log.pack(side=tk.LEFT, padx=(0, 8))
                    btn_close.config(state=tk.NORMAL)
            except queue.Empty:
                break

        root.after(80, process_queues)

    def on_start_click():
        gpu_checkbox.config(state=tk.DISABLED)
        btn_start.config(state=tk.DISABLED, text="Building...")
        btn_close.config(state=tk.DISABLED)
        log_text.delete("1.0", tk.END)
        progress_bar['value'] = 0

        worker = BuildWorker(
            include_gpu=gpu_var.get(),
            log_callback=lambda msg: log_queue.put(msg),
            step_callback=lambda s, t, d: step_queue.put((s, t, d)),
            done_callback=lambda ok, step, tail: done_queue.put((ok, step, tail))
        )
        worker_ref[0] = worker
        threading.Thread(target=worker.build, daemon=True).start()

    def on_launch_click():
        exe_path = os.path.join(OUTPUT_APP_DIR, "WhisperFlow.exe")
        if os.path.exists(exe_path):
            subprocess.Popen([exe_path], cwd=OUTPUT_APP_DIR)
            root.destroy()
        else:
            messagebox.showerror("Error", f"Executable not found at:\n{exe_path}")

    def on_open_folder_click():
        if os.path.exists(OUTPUT_APP_DIR):
            os.startfile(OUTPUT_APP_DIR)
        else:
            messagebox.showerror("Error", f"Directory not found:\n{OUTPUT_APP_DIR}")

    def on_view_log_click():
        if os.path.exists(BUILD_LOG_PATH):
            os.startfile(BUILD_LOG_PATH)

    # Action Buttons
    btn_start = tk.Button(
        button_bar,
        text="Start Build",
        font=("Segoe UI", 10, "bold"),
        bg=ACCENT_PURPLE,
        fg=TEXT_LIGHT,
        activebackground="#6d28d9",
        activeforeground=TEXT_LIGHT,
        relief=tk.FLAT,
        padx=18,
        pady=6,
        cursor="hand2",
        command=on_start_click
    )
    btn_start.pack(side=tk.LEFT, padx=(0, 8))

    btn_launch = tk.Button(
        button_bar,
        text="Launch WhisperFlow",
        font=("Segoe UI", 10, "bold"),
        bg="#16a34a",
        fg=TEXT_LIGHT,
        activebackground="#15803d",
        activeforeground=TEXT_LIGHT,
        relief=tk.FLAT,
        padx=18,
        pady=6,
        cursor="hand2",
        command=on_launch_click
    )

    btn_open_folder = tk.Button(
        button_bar,
        text="Open Folder",
        font=("Segoe UI", 10),
        bg=CARD_BG,
        fg=TEXT_LIGHT,
        relief=tk.FLAT,
        padx=14,
        pady=6,
        cursor="hand2",
        command=on_open_folder_click
    )

    btn_view_log = tk.Button(
        button_bar,
        text="Open Log File",
        font=("Segoe UI", 10),
        bg=CARD_BG,
        fg=TEXT_LIGHT,
        relief=tk.FLAT,
        padx=14,
        pady=6,
        cursor="hand2",
        command=on_view_log_click
    )

    btn_close = tk.Button(
        button_bar,
        text="Cancel",
        font=("Segoe UI", 10),
        bg=CARD_BG,
        fg=TEXT_LIGHT,
        relief=tk.FLAT,
        padx=14,
        pady=6,
        cursor="hand2",
        command=root.destroy
    )
    btn_close.pack(side=tk.RIGHT)

    root.after(100, process_queues)
    root.mainloop()


# =========================================================================
# CLI Fallback Mode
# =========================================================================
def run_cli(include_gpu=False):
    print("=" * 60)
    print("Whisper Flow Standalone Builder (Console Mode)")
    print("=" * 60)
    
    def log_cb(msg):
        print(msg)

    def step_cb(step, total, desc):
        print(f"\n[Step {step}/{total}] {desc}...")

    event_done = threading.Event()
    results = {}

    def done_cb(success, err_step, log_tail):
        results['success'] = success
        results['err_step'] = err_step
        results['log_tail'] = log_tail
        event_done.set()

    worker = BuildWorker(
        include_gpu=include_gpu,
        log_callback=log_cb,
        step_callback=step_cb,
        done_callback=done_cb
    )
    threading.Thread(target=worker.build, daemon=True).start()
    event_done.wait()

    if results.get('success'):
        print("\nBUILD SUCCESSFUL! WhisperFlow.exe created in WhisperFlow_App\\")
        sys.exit(0)
    else:
        print(f"\nBUILD FAILED during step: {results.get('err_step')}")
        print("Check build_log.txt for full output.")
        sys.exit(1)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        include_gpu = "--gpu" in sys.argv
        run_cli(include_gpu=include_gpu)
    else:
        try:
            run_gui()
        except Exception as e:
            print(f"Tkinter GUI could not be initialized ({e}). Falling back to console mode...")
            include_gpu = "--gpu" in sys.argv
            run_cli(include_gpu=include_gpu)
