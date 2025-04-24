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
    def __init__(self, master, placeholder, h=60):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.result = None
        self.placeholder = placeholder

        # Transparent background
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

        # Text input area with placeholder
        self.entry = tk.Text(self, width=40, height=h//10, bd=0, bg='white', fg='grey')
        self.entry.insert("1.0", placeholder)
        self.entry.pack(padx=5, pady=5)
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<FocusOut>", self._add_placeholder)
        self.entry.bind("<Return>", self._on_return)

        # Send button
        btn = tk.Button(self, text="Send", command=self.on_send, bd=0)
        btn.pack(fill='x', padx=5, pady=(0,5))

        position_bottom_right(self, 300, h+20)
        self.deiconify()

    def _clear_placeholder(self, event):
        content = self.entry.get("1.0", "end-1c")
        if content == self.placeholder:
            self.entry.delete("1.0", tk.END)
            self.entry.config(fg='black')

    def _add_placeholder(self, event):
        content = self.entry.get("1.0", "end-1c").strip()
        if not content:
            self.entry.insert("1.0", self.placeholder)
            self.entry.config(fg='grey')

    def _on_return(self, event):
        self.on_send()
        return "break"

    def on_send(self):
        text = self.entry.get("1.0", "end-1c").strip()
        if text and text != self.placeholder:
            self.result = text
        self.destroy()

class ResponseDialog(tk.Toplevel):
    def __init__(self, master, message, trans_color):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.next_prompt = False
        self.new_prefix = False

        # Transparent background
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

        btn_prompt = tk.Button(
            btn_frame, text="New Prompt", command=self.on_new_prompt,
            bd=0, bg=trans_color or 'white', highlightthickness=0
        )
        btn_prefix = tk.Button(
            btn_frame, text="New Prefix", command=self.on_new_prefix,
            bd=0, bg=trans_color or 'white', highlightthickness=0
        )

        btn_prompt.pack(side='left', expand=True, fill='x', padx=2)
        btn_prefix.pack(side='right', expand=True, fill='x', padx=2)

        self.update_idletasks()
        btn_h = btn_prompt.winfo_reqheight()
        height = lbl.winfo_reqheight() + btn_h + 25
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

    # 1) API-key dialog
    api_dlg = InputDialog(root, placeholder="Enter your Gemini API key...", h=30)
    root.wait_window(api_dlg)
    api_key = getattr(api_dlg, 'result', None)
    if not api_key:
        raise RuntimeError("No API key provided.")
    trans_color = getattr(api_dlg, 'trans', None)

    client = genai.Client(api_key=api_key)

    # 2) Prefix / Prompt / Response loop
    while True:
        # Prefix input
        prefix_dlg = InputDialog(root, placeholder="Enter prompt prefix...", h=30)
        root.wait_window(prefix_dlg)
        prefix = getattr(prefix_dlg, 'result', "")
        if not prefix:
            break

        while True:
            # Prompt input
            prompt_dlg = InputDialog(root, placeholder="Enter your question...", h=30)
            root.wait_window(prompt_dlg)
            prompt_text = getattr(prompt_dlg, 'result', "")
            if not prompt_text:
                break

            # Send to Gemini
            full_prompt = prefix + " " + prompt_text
            try:
                resp = client.models.generate_content(
                    model="gemini-2.0-flash-001",
                    contents=full_prompt
                )
                reply = resp.text.strip()
            except Exception as e:
                reply = f"[API error] {e}"

            # Show response
            resp_dlg = ResponseDialog(root, reply, trans_color)
            root.wait_window(resp_dlg)
            if resp_dlg.new_prefix:
                break  # back to prefix
            if not resp_dlg.next_prompt:
                root.destroy()
                sys.exit()

    root.destroy()
