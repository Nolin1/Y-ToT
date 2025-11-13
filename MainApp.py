import os
import sys
import shutil
import subprocess
import threading
import queue
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "YouTube Video Downloader"
SCRIPT_DIR = Path(__file__).parent.resolve()


def default_videos_folder():
    if os.name == "nt":
        return os.path.join(os.environ.get("USERPROFILE", ""), "Videos")
    return str(Path.home() / "Videos")


def find_executable(names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
        win = Path(r"C:\Windows") / name
        if win.exists():
            return str(win)
    return None


def find_yt_dlp():
    return find_executable(["yt-dlp.exe", "yt-dlp"])


def find_ffmpeg():
    return find_executable(["ffmpeg.exe", "ffmpeg"])


def run_helper_script(script_name):
    path = SCRIPT_DIR / script_name
    if not path.exists():
        return (1, f"Missing helper script: {path.name}")
    try:
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
        return (proc.returncode, proc.stdout + proc.stderr)
    except Exception as e:
        return (1, f"Exception: {e}")


class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("480x600")
        self.resizable(False, False)
        self.output_queue = queue.Queue()
        self.downloading = False
        self.proc = None

        self.yt_dlp_path = None
        self.ffmpeg_path = None

        self._build_ui()
        self._check_tools()
        self.after(200, self._flush_output_queue)

    def _build_ui(self):
        # Center frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")

        title = ctk.CTkLabel(self.main_frame, text=APP_TITLE, font=("Arial", 22, "bold"))
        title.pack(pady=(20, 10))

        # URL field
        url_label = ctk.CTkLabel(self.main_frame, text="YouTube URL:")
        url_label.pack(pady=(10, 5))
        self.url_entry = ctk.CTkEntry(self.main_frame, width=380, placeholder_text="Paste your video link here...")
        self.url_entry.pack()
        paste_btn = ctk.CTkButton(self.main_frame, text="Paste", width=100, command=self._paste_clipboard)
        paste_btn.pack(pady=(8, 15))

        # Save folder
        folder_label = ctk.CTkLabel(self.main_frame, text="Save Location:")
        folder_label.pack(pady=(5, 5))
        self.save_path_var = ctk.StringVar(value=default_videos_folder())
        folder_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        folder_frame.pack()
        self.save_entry = ctk.CTkEntry(folder_frame, textvariable=self.save_path_var, width=280)
        self.save_entry.pack(side="left", padx=(0, 8))
        choose_btn = ctk.CTkButton(folder_frame, text="Choose", width=80, command=self._choose_folder)
        choose_btn.pack(side="left")

        # Start download button
        self.start_btn = ctk.CTkButton(
            self.main_frame,
            text="Start Download",
            width=200,
            height=40,
            font=("Arial", 14, "bold"),
            command=self._start_clicked,
        )
        self.start_btn.pack(pady=(20, 15))

        # Status box
        status_label = ctk.CTkLabel(self.main_frame, text="Status:")
        status_label.pack(pady=(5, 5))
        self.status_box = ctk.CTkTextbox(self.main_frame, width=400, height=180)
        self.status_box.pack(padx=10, pady=(5, 20))

    def _paste_clipboard(self):
        try:
            text = self.clipboard_get()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, text.strip())
        except Exception:
            messagebox.showwarning("Clipboard", "Could not paste from clipboard.")

    def _choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if chosen:
            self.save_path_var.set(chosen)

    def _check_tools(self):
        self._append_status("Checking for yt-dlp and ffmpeg...")
        self.yt_dlp_path = find_yt_dlp()
        self.ffmpeg_path = find_ffmpeg()

        if not self.yt_dlp_path:
            self._append_status("yt-dlp missing. Will install when needed.")
        else:
            self._append_status(f"yt-dlp found: {self.yt_dlp_path}")

        if not self.ffmpeg_path:
            self._append_status("ffmpeg missing. Will install when needed.")
        else:
            self._append_status(f"ffmpeg found: {self.ffmpeg_path}")

    def _start_clicked(self):
        if self.downloading:
            return
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a YouTube link first.")
            return

        save_dir = self.save_path_var.get()
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except Exception as e:
                messagebox.showerror("Folder Error", str(e))
                return

        # check/install tools if missing
        if not self.yt_dlp_path:
            self._append_status("Installing yt-dlp...")
            code, out = run_helper_script("yt_dlp_cmd.py")
            self._append_status(out)
            self.yt_dlp_path = find_yt_dlp()
            if not self.yt_dlp_path:
                messagebox.showerror("yt-dlp", "yt-dlp install failed.")
                return

        if not self.ffmpeg_path:
            self._append_status("Installing ffmpeg...")
            code, out = run_helper_script("ffmpeg_cmd.py")
            self._append_status(out)
            self.ffmpeg_path = find_ffmpeg()
            if not self.ffmpeg_path:
                messagebox.showerror("ffmpeg", "ffmpeg install failed.")
                return

        # start download
        self._start_download_thread(url, save_dir)

    def _start_download_thread(self, url, folder):
        self.downloading = True
        self.start_btn.configure(state="disabled")
        self._append_status("Starting download...")
        thread = threading.Thread(target=self._download_worker, args=(url, folder), daemon=True)
        thread.start()

    def _download_worker(self, url, folder):
        try:
            output_template = os.path.join(folder, "%(title).100s.%(ext)s")
            cmd = [
                self.yt_dlp_path,
                url,
                "-f",
                "bestvideo+bestaudio/best",
                "--merge-output-format",
                "mp4",
                "-o",
                output_template,
                "--newline",
            ]

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True)
            self.proc = proc
            for line in proc.stdout:
                self._append_status(line.strip())
            code = proc.wait()
            if code == 0:
                self._append_status("✅ Download completed successfully!")
            else:
                self._append_status(f"❌ Download failed (exit {code})")
        except Exception as e:
            self._append_status(f"Error: {e}")
        finally:
            self.downloading = False
            self.after(0, lambda: self.start_btn.configure(state="normal"))

    def _append_status(self, text):
        self.output_queue.put(text)

    def _flush_output_queue(self):
        while not self.output_queue.empty():
            text = self.output_queue.get_nowait()
            self.status_box.insert("end", text + "\n")
            self.status_box.see("end")
        self.after(200, self._flush_output_queue)


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
