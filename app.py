import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import speech_recognition as sr
import pyperclip
import datetime
import os

LANGUAGES = {
    "🇲🇳 Монгол": "mn-MN",
    "🇺🇸 Англи (US)": "en-US",
    "🇬🇧 Англи (UK)": "en-GB",
    "🇷🇺 Орос": "ru-RU",
    "🇨🇳 Хятад": "zh-CN",
    "🇯🇵 Япон": "ja-JP",
    "🇰🇷 Солонгос": "ko-KR",
    "🇩🇪 Герман": "de-DE",
    "🇫🇷 Франц": "fr-FR",
    "🇹🇷 Турк": "tr-TR",
}

class SpeechToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Яриа → Текст | Speech to Text")
        self.root.geometry("720x560")
        self.root.minsize(600, 480)
        self.root.configure(bg="#F8F7F4")

        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

        self.is_recording = False
        self.record_thread = None
        self.transcript = ""

        self._build_ui()
        self._check_mic()

    def _build_ui(self):
        root = self.root

        # Title bar
        title_frame = tk.Frame(root, bg="#F8F7F4")
        title_frame.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(title_frame, text="Яриа → Текст", font=("Segoe UI", 18, "bold"),
                 bg="#F8F7F4", fg="#1A1A1A").pack(side="left")

        tk.Label(title_frame, text="Speech Recognition", font=("Segoe UI", 12),
                 bg="#F8F7F4", fg="#888880").pack(side="left", padx=(12, 0), pady=(4, 0))

        # Status bar
        status_frame = tk.Frame(root, bg="#EEEEE8", bd=0, relief="flat",
                                 highlightthickness=1, highlightbackground="#D3D1C7")
        status_frame.pack(fill="x", padx=24, pady=(14, 0))

        inner = tk.Frame(status_frame, bg="#EEEEE8")
        inner.pack(fill="x", padx=12, pady=8)

        self.status_dot = tk.Label(inner, text="●", font=("Segoe UI", 10),
                                    bg="#EEEEE8", fg="#639922")
        self.status_dot.pack(side="left")

        self.status_label = tk.Label(inner, text="Бэлэн байна",
                                      font=("Segoe UI", 11), bg="#EEEEE8", fg="#5F5E5A")
        self.status_label.pack(side="left", padx=(6, 0))

        # Controls row
        ctrl = tk.Frame(root, bg="#F8F7F4")
        ctrl.pack(fill="x", padx=24, pady=(14, 0))

        # Mic button
        self.mic_btn = tk.Button(ctrl, text="⏺  Бичлэг эхлүүлэх",
                                  font=("Segoe UI", 11, "bold"),
                                  bg="#FFFFFF", fg="#1A1A1A",
                                  activebackground="#F0EEE8",
                                  relief="flat", bd=0, padx=16, pady=8,
                                  cursor="hand2", command=self.toggle_recording,
                                  highlightthickness=1, highlightbackground="#C0BEB4")
        self.mic_btn.pack(side="left")

        # Language selector
        tk.Label(ctrl, text="Хэл:", font=("Segoe UI", 11),
                 bg="#F8F7F4", fg="#5F5E5A").pack(side="left", padx=(16, 6))

        self.lang_var = tk.StringVar(value="🇲🇳 Монгол")
        lang_menu = ttk.Combobox(ctrl, textvariable=self.lang_var,
                                  values=list(LANGUAGES.keys()),
                                  width=18, state="readonly", font=("Segoe UI", 11))
        lang_menu.pack(side="left")

        # Continuous toggle
        self.continuous_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(ctrl, text="Тасралтгүй", variable=self.continuous_var,
                               font=("Segoe UI", 10), bg="#F8F7F4", fg="#5F5E5A",
                               activebackground="#F8F7F4", cursor="hand2")
        chk.pack(side="left", padx=(14, 0))

        # Text area
        text_frame = tk.Frame(root, bg="#FFFFFF", bd=0,
                               highlightthickness=1, highlightbackground="#D3D1C7")
        text_frame.pack(fill="both", expand=True, padx=24, pady=(12, 0))

        self.text_area = scrolledtext.ScrolledText(text_frame,
                                                    font=("Segoe UI", 13),
                                                    wrap="word", bd=0, relief="flat",
                                                    bg="#FFFFFF", fg="#1A1A1A",
                                                    insertbackground="#1A1A1A",
                                                    selectbackground="#B5D4F4",
                                                    padx=14, pady=12)
        self.text_area.pack(fill="both", expand=True)
        self.text_area.tag_configure("interim", foreground="#888780", font=("Segoe UI", 13, "italic"))

        # Word count
        self.count_label = tk.Label(root, text="0 үг · 0 тэмдэгт",
                                     font=("Segoe UI", 10), bg="#F8F7F4", fg="#B4B2A9")
        self.count_label.pack(anchor="e", padx=28)

        # Bottom buttons
        bottom = tk.Frame(root, bg="#F8F7F4")
        bottom.pack(fill="x", padx=24, pady=(8, 20))

        for text, cmd in [("Хуулах", self.copy_text),
                           ("Хадгалах", self.save_text),
                           ("Цэвэрлэх", self.clear_text)]:
            b = tk.Button(bottom, text=text, font=("Segoe UI", 10),
                          bg="#EEEEE8", fg="#444441", activebackground="#D3D1C7",
                          relief="flat", bd=0, padx=14, pady=6,
                          cursor="hand2", command=cmd,
                          highlightthickness=1, highlightbackground="#C0BEB4")
            b.pack(side="left", padx=(0, 8))

        # Version label
        tk.Label(bottom, text="Google Speech API ашиглана · Интернэт шаардлагатай",
                 font=("Segoe UI", 9), bg="#F8F7F4", fg="#B4B2A9").pack(side="right")

    def _check_mic(self):
        try:
            mics = sr.Microphone.list_microphone_names()
            if not mics:
                self._set_status("⚠ Микрофон олдсонгүй", "#BA7517")
        except Exception:
            self._set_status("⚠ Микрофон шалгаж чадсангүй", "#BA7517")

    def _set_status(self, text, color="#5F5E5A", dot_color=None):
        self.status_label.config(text=text, fg=color)
        self.status_dot.config(fg=dot_color or color)

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.mic_btn.config(text="⏹  Зогсоох", bg="#FCEBEB",
                             fg="#A32D2D", highlightbackground="#F09595")
        self._set_status("Сонсож байна...", "#E24B4A", "#E24B4A")
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.record_thread.start()

    def stop_recording(self):
        self.is_recording = False
        self.mic_btn.config(text="⏺  Бичлэг эхлүүлэх", bg="#FFFFFF",
                             fg="#1A1A1A", highlightbackground="#C0BEB4")
        self._set_status("Бэлэн байна", "#639922", "#639922")

    def _record_loop(self):
        lang = LANGUAGES.get(self.lang_var.get(), "mn-MN")
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            while self.is_recording:
                try:
                    self.root.after(0, lambda: self._set_status("Ярих хүлээж байна...", "#E24B4A", "#E24B4A"))
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=30)
                    self.root.after(0, lambda: self._set_status("Таниж байна...", "#185FA5", "#185FA5"))
                    text = self.recognizer.recognize_google(audio, language=lang)
                    self.root.after(0, self._append_text, text)
                    if not self.continuous_var.get():
                        self.root.after(0, self.stop_recording)
                        break
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.root.after(0, lambda: self._set_status("Яриа ойлгогдсонгүй, дахин оролдоно уу", "#BA7517", "#BA7517"))
                except sr.RequestError as e:
                    self.root.after(0, lambda: self._set_status(f"Интернэт алдаа: {e}", "#A32D2D", "#A32D2D"))
                    self.root.after(0, self.stop_recording)
                    break
                except Exception as e:
                    self.root.after(0, lambda: self._set_status(f"Алдаа: {e}", "#A32D2D", "#A32D2D"))
                    break

    def _append_text(self, text):
        current = self.text_area.get("1.0", "end-1c")
        separator = " " if current and not current.endswith("\n") else ""
        self.text_area.insert("end", separator + text)
        self.text_area.see("end")
        self._update_count()
        self._set_status("Сонсож байна...", "#E24B4A", "#E24B4A")

    def _update_count(self):
        text = self.text_area.get("1.0", "end-1c").strip()
        words = len(text.split()) if text else 0
        chars = len(text)
        self.count_label.config(text=f"{words} үг · {chars} тэмдэгт")

    def copy_text(self):
        text = self.text_area.get("1.0", "end-1c").strip()
        if text:
            try:
                pyperclip.copy(text)
                self._set_status("Хуулагдлаа!", "#639922", "#639922")
                self.root.after(2000, lambda: self._set_status("Бэлэн байна", "#639922", "#639922"))
            except Exception:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)

    def save_text(self):
        text = self.text_area.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("Мэдэгдэл", "Хадгалах текст байхгүй байна.")
            return
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"яриа_{date_str}.txt",
            filetypes=[("Text файл", "*.txt"), ("Бүгд", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._set_status(f"Хадгалагдлаа: {os.path.basename(path)}", "#639922", "#639922")

    def clear_text(self):
        if messagebox.askyesno("Цэвэрлэх", "Текстийг цэвэрлэх үү?"):
            self.text_area.delete("1.0", "end")
            self._update_count()


def main():
    root = tk.Tk()
    root.resizable(True, True)
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = SpeechToTextApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
