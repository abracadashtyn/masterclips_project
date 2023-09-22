from pycode.config.config import Config
from pycode.objects.posting_app import PostingApp
import tkinter as tk

if __name__ == '__main__':
    gui_root = tk.Tk()
    config = Config()
    app_handle = PostingApp(gui_root, config)
    gui_root.mainloop()
