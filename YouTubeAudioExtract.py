import os
import sys
import threading
import shutil
import time
from tkinter import (
    Tk, Label, Entry, Button, StringVar, filedialog,
    messagebox, ttk, Frame
)
import yt_dlp

# Detect base path (support frozen executable)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))


def get_ffmpeg_path():
    local_ffmpeg = os.path.join(base_path, "ffmpeg_bin", "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path
    raise FileNotFoundError("ffmpeg executable not found. Please install FFmpeg or include it in the 'ffmpeg_bin' folder.")


def get_ffprobe_path():
    local_ffprobe = os.path.join(base_path, "ffmpeg_bin", "ffprobe.exe")
    if os.path.exists(local_ffprobe):
        return local_ffprobe
    ffprobe_in_path = shutil.which("ffprobe")
    if ffprobe_in_path:
        return ffprobe_in_path
    raise FileNotFoundError("ffprobe executable not found. Please install FFprobe or include it in the 'ffmpeg_bin' folder.")


# Try locating FFmpeg and FFprobe
try:
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()
except FileNotFoundError as e:
    ffmpeg_path = None
    ffprobe_path = None
    print(f"⚠️ {e}")

# Allowed audio formats (standard)
ALLOWED_FORMATS = {"mp3", "m4a", "wav", "aac", "flac", "opus", "alac"}

def download_audio_with_progress(youtube_url, output_dir, fmt,
                                  status_var, progress_var, progress_bar, root):
    status_var.set("Starting...")
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        start_time = time.time()

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': fmt,
                'preferredquality': '192',
            }],
        }

        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
        if ffprobe_path:
            ydl_opts['ffprobe_location'] = ffprobe_path

        def progress_hook(d):
            if d.get('status') == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                if total:
                    progress = downloaded / total
                    percent = int(progress * 100)

                    elapsed = time.time() - start_time
                    eta = (elapsed / progress - elapsed) if progress > 0 else 0
                    eta_str = time.strftime("%M:%S", time.gmtime(eta))

                    progress_bar['value'] = percent
                    progress_var.set(f"{percent}%")
                    status_var.set(f"Downloading... {percent}% | ETA: {eta_str}")

            elif d.get('status') == 'finished':
                progress_bar['value'] = 100
                progress_var.set("100%")
                status_var.set("Converting audio...")

        ydl_opts['progress_hooks'] = [progress_hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        status_var.set("✅ Download Complete")

        def show_and_exit():
            messagebox.showinfo("Download Complete", "Audio downloaded and converted successfully.")
            root.destroy()

        root.after(100, show_and_exit)

    except Exception as e:
        status_var.set("❌ Error")
        messagebox.showerror("Download Error", str(e))


def start_download():
    url = url_var.get().strip()
    out = output_dir_var.get().strip()
    fmt = format_var.get().strip().lower()

    # Check for missing info
    if not url or not out or not fmt:
        messagebox.showwarning("Missing Info", "Please fill all fields.")
        return

    # Validate format against allowed list
    if fmt not in ALLOWED_FORMATS:
        messagebox.showerror("Invalid Format", f"'{fmt}' is not a supported audio format.\n\nAllowed formats: {', '.join(sorted(ALLOWED_FORMATS))}")
        root.destroy()  # Close the app immediately after showing the error
        return

    threading.Thread(
        target=download_audio_with_progress,
        args=(url, out, fmt, status_var, progress_var, progress_bar, root),
        daemon=True
    ).start()


def browse_output_dir():
    path = filedialog.askdirectory()
    if path:
        output_dir_var.set(path)


# ---------------- GUI Setup ---------------- #
root = Tk()
root.title("🎵 YouTube Audio Downloader")
root.geometry("520x340")
root.resizable(False, False)

url_var = StringVar()
output_dir_var = StringVar(value=os.path.join(base_path, "downloads"))
format_var = StringVar(value="mp3")
progress_var = StringVar(value="0%")
status_var = StringVar(value="Ready")

# --- URL Entry ---
Label(root, text="🎬 YouTube Video URL:").pack(anchor="w", padx=12, pady=(10, 0))
Entry(root, textvariable=url_var, width=65).pack(padx=10, pady=5)

# --- Output Directory ---
Label(root, text="📁 Output Folder:").pack(anchor="w", padx=12, pady=(5, 0))
output_frame = Frame(root)
output_frame.pack(fill="x", padx=10)
Entry(output_frame, textvariable=output_dir_var, width=50).pack(side="left", padx=(0, 5), pady=5)
Button(output_frame, text="Browse", command=browse_output_dir).pack(side="left")

# --- Format Entry ---
Label(root, text="🎧 Audio Format (e.g., mp3, m4a, wav):").pack(anchor="w", padx=12, pady=(5, 0))
Entry(root, textvariable=format_var, width=10).pack(padx=10, pady=5, anchor="w")

# --- Download Button ---
Button(root, text="Download Audio", command=start_download,
       bg="#4CAF50", fg="white", font=('Arial', 12, 'bold')).pack(pady=15, padx=10, fill="x")

# --- Progress Bar and Status ---
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=5)
Label(root, textvariable=status_var).pack()

root.mainloop()
