import tkinter as tk
from tkinter import ttk

class IndividualTab(ttk.Frame):
    def __init__(self, parent, puente):
        super().__init__(parent)
        self.puente = puente
        self.angulos = {"j1x": 90, "j1y": 90, "j2x": 90, "j2y": 90}
        self.sliders = {}
        self.labels = {}
        self._widgets_listos = False
        
        self._build_ui()
        self._set_ui_state()
        self._widgets_listos = True

    def _build_ui(self):
        # Crear filas para cada servo
        for key, val in self.angulos.items():
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=5)
            
            ttk.Label(row, text=key.upper()+":", width=6).pack(side=tk.LEFT)
            
            # 1. Crear Label PRIMERO
            lbl = ttk.Label(row, text=f"{int(val)}°", width=5)
            lbl.pack(side=tk.LEFT)
            self.labels[key] = lbl
            
            # 2. Crear Slider DESPUÉS
            slider = ttk.Scale(row, from_=0, to=180, orient=tk.HORIZONTAL,
                              command=lambda val, k=key: self._on_slider_change(k, val))
            slider.set(val)
            slider.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
            self.sliders[key] = slider
            
            ttk.Button(row, text="Centrar", command=lambda k=key: self._center_servo(k)).pack(side=tk.LEFT, padx=5)

        # Botón general
        ttk.Button(self, text="Centrar todos", command=self._center_all).pack(pady=20)

    def _set_ui_state(self):
        state = "normal" if self.puente else "disabled"
        for slider in self.sliders.values():
            slider.config(state=state)

    def _on_slider_change(self, key, val):
        if not self._widgets_listos:
            return
            
        val = int(float(val))
        self.angulos[key] = val
        if key in self.labels:
            self.labels[key].config(text=f"{val}°")
        self._send_update()

    def _center_servo(self, key):
        if key in self.sliders:
            self.sliders[key].set(90)
            # _on_slider_change es llamado automáticamente por el cambio del slider

    def _center_all(self):
        for key in self.angulos:
            if key in self.sliders:
                self.sliders[key].set(90)
        # _on_slider_change es llamado automáticamente para cada uno

    def _send_update(self):
        if self.puente:
            self.puente.set_angulos(**self.angulos)
