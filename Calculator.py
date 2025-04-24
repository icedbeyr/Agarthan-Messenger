import os
import sys
import tkinter as tk
from google import genai

def position_bottom_right(win, width, height):
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = sw - width
    y = sh - height
    win.geometry(f"{width}x{height}+{x}+{y}")

class InputDialog(tk.Toplevel):
    def __init__(self, master, prompt, h=60):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.result = None

        if sys.platform.startswith("win"):
            self.trans = "magenta"
            self.config(bg=self.trans)
            self.attributes('-transparentcolor', self.trans)
        elif sys.platform == "darwin":
            self.attributes('-transparent', True)
            self.trans = None
        else:
            self.attributes('-alpha', 0.85)
            self.trans = None

        self.entry = tk.Text(self, width=40, height=h//10, bd=0, bg='white')
        self.entry.pack(padx=5, pady=5)
        self.entry.bind("<Return>", self._on_return)

        self.button = tk.Button(self, text="Send", command=self.on_send, bd=0)
        self.button.pack(fill='x', padx=5, pady=(0,5))

        position_bottom_right(self, 300, h+20)
        self.deiconify()

    def _on_return(self, event):
        self.on_send()
        return "break"

    def on_send(self):
        self.result = self.entry.get("1.0", tk.END).strip()
        self.destroy()

class ResponseDialog(tk.Toplevel):
    def __init__(self, master, message, trans_color):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.next_prompt = False
        self.new_prefix = False

        if trans_color:
            self.config(bg=trans_color)
            self.attributes('-transparentcolor', trans_color)
        elif sys.platform == "darwin":
            self.attributes('-transparent', True)
        else:
            self.attributes('-alpha', 0.85)

        lbl = tk.Label(self, text=message, bg='white', wraplength=280, justify='left')
        lbl.pack(padx=10, pady=(10,5))

        btn_frame = tk.Frame(self, bg=trans_color or 'white')
        btn_frame.pack(padx=10, pady=(0,10), fill='x')

        self.btn_prompt = tk.Button(
            btn_frame, text="New Prompt", command=self.on_new_prompt,
            bd=0, bg=trans_color or 'white', highlightthickness=0
        )
        self.btn_prefix = tk.Button(
            btn_frame, text="New Prefix", command=self.on_new_prefix,
            bd=0, bg=trans_color or 'white', highlightthickness=0
        )

        self.btn_prompt.pack(side='left', expand=True, fill='x', padx=2)
        self.btn_prefix.pack(side='right', expand=True, fill='x', padx=2)

        self.update_idletasks()
        height = lbl.winfo_reqheight() + self.btn_prompt.winfo_reqheight() + 25
        position_bottom_right(self, 300, height)
        self.deiconify()

    def on_new_prompt(self):
        self.next_prompt = True
        self.destroy()

    def on_new_prefix(self):
        self.new_prefix = True
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # Use your actual API key here
    api_key = "ENTER_GEMINI_API_KEY_HERE"
    client = genai.Client(api_key=api_key)

    sample = InputDialog(root, "Prefix", h=60)
    trans_color = getattr(sample, 'trans', None)
    sample.destroy()

    prefix = ""
    while True:
        # Prefix input
        prefix_box = InputDialog(root, "Enter prompt prefix:", h=30)
        root.wait_window(prefix_box)
        prefix = getattr(prefix_box, 'result', "")
        if not prefix:
            break

        while True:
            # Prompt input
            prompt_box = InputDialog(root, "Prompt:", h=15)
            root.wait_window(prompt_box)
            prompt_text = getattr(prompt_box, 'result', "")
            if not prompt_text:
                break

            full_prompt = prefix + " " + prompt_text
            try:
                resp = client.models.generate_content(
                    model="gemini-2.0-flash-001",
                    contents=full_prompt
                )
                reply = resp.text.strip()
            except Exception as e:
                reply = f"[API error] {e}"

            result_box = ResponseDialog(root, reply, trans_color)
            root.wait_window(result_box)

            if result_box.new_prefix:
                break  # go back to change prefix
            if not result_box.next_prompt:
                root.destroy()
                sys.exit()
