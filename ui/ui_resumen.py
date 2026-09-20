import tkinter as tk
from tkinter import ttk

class ResumenTab(ttk.Frame):
    def __init__(self, parent, puente):
        super().__init__(parent)
        self.puente = puente
        tk.Label(self, text="Resumen de Valores").pack(pady=20)
