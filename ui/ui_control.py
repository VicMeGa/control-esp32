import tkinter as tk
from tkinter import ttk

class ControlTab(ttk.Frame):
    def __init__(self, parent, puente):
        super().__init__(parent)
        self.puente = puente
        tk.Label(self, text="Panel de Control Principal").pack(pady=20)
