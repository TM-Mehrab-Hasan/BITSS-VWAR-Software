import tkinter as tk

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    # def show_tip(self, event=None):
    #     if self.tipwindow:
    #         return
    #     x, y, cx, cy = self.widget.bbox("insert")
    #     x = x + self.widget.winfo_rootx() + 25
    #     y = y + self.widget.winfo_rooty() + 20
    #     self.tipwindow = tw = tk.Toplevel(self.widget)
    #     tw.wm_overrideredirect(True)
    #     tw.geometry(f"+{x}+{y}")
    #     label = tk.Label(tw, text=self.text, justify=tk.LEFT,
    #                      background="yellow", relief=tk.SOLID, borderwidth=1,
    #                      font=("tahoma", "10", "normal"))
    #     label.pack(ipadx=1)
    
    
    def show_tip(self, event=None):
        if self.tipwindow:
            return
        self.id = self.widget.after(400, self._create_tip)  # 400ms delay

    def _create_tip(self):
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="yellow", relief=tk.SOLID, borderwidth=1,
                        font=("tahoma", "10", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if hasattr(self, "id"):
            self.widget.after_cancel(self.id)
            del self.id
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
