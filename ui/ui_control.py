import tkinter as tk
from tkinter import ttk, messagebox
import perfiles

class ControlTab(ttk.Frame):
    def __init__(self, parent, puente):
        super().__init__(parent)
        self.puente = puente
        self.master_app = parent.master # Referencia a App
        
        self.perfil_actual = self.master_app.perfil_activo
        self.limites = perfiles.obtener_perfil(self.perfil_actual)
        self.angulos_actuales = {eje: self.limites[eje]["centro"] for eje in self.limites}
        
        self.canvas_size = 200
        self.canvas_objects = {}
        self._widgets_listos = False
        
        self._build_ui()
        self._widgets_listos = True
        self._update_ui_state()

    def _build_ui(self):
        # 1. Selector de perfil
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_frame, text="Perfil:").pack(side=tk.LEFT)
        self.profile_combo = ttk.Combobox(top_frame, values=perfiles.listar_perfiles(), state="readonly")
        self.profile_combo.set(self.perfil_actual)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)

        # 2. Canvas
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(pady=10)
        
        self._create_canvas(canvas_frame, "J1X", "J1Y", "Joystick 1")
        self._create_canvas(canvas_frame, "J2X", "J2Y", "Joystick 2")

    def _create_canvas(self, parent, key_x, key_y, label):
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(frame, text=label).pack()
        canvas = tk.Canvas(frame, width=self.canvas_size, height=self.canvas_size, bg="white", highlightbackground="gray")
        canvas.pack()
        
        cx, cy = self.canvas_size // 2, self.canvas_size // 2
        circle = canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill="blue")
        
        lbl = ttk.Label(frame, text=f"{key_x}: {self.angulos_actuales[key_x]}° | {key_y}: {self.angulos_actuales[key_y]}°")
        lbl.pack()
        
        self.canvas_objects[key_x] = {"canvas": canvas, "circle": circle, "lbl": lbl, "key_x": key_x, "key_y": key_y}
        
        canvas.bind("<B1-Motion>", lambda event: self._on_drag(event, key_x, key_y))
        canvas.bind("<ButtonRelease-1>", lambda event: self._on_release(key_x, key_y))

    def _on_drag(self, event, key_x, key_y):
        if not self.puente: return
        
        x = max(0, min(event.x, self.canvas_size))
        y = max(0, min(event.y, self.canvas_size))
        
        self.angulos_actuales[key_x] = self._map_to_angle(x, key_x)
        self.angulos_actuales[key_y] = self._map_to_angle(y, key_y)
        
        self._update_canvas(key_x)
        self._send_update()

    def _map_to_angle(self, pos, eje):
        lims = self.limites[eje]
        if pos < 100:
            return int(lims["min"] + (lims["centro"] - lims["min"]) * (pos / 100))
        else:
            return int(lims["centro"] + (lims["max"] - lims["centro"]) * ((pos - 100) / 100))

    def _on_release(self, key_x, key_y):
        self._animate_center(key_x, key_y, steps=10)

    def _animate_center(self, key_x, key_y, steps):
        if steps == 0:
            self.angulos_actuales[key_x] = self.limites[key_x]["centro"]
            self.angulos_actuales[key_y] = self.limites[key_y]["centro"]
            self._update_canvas(key_x)
            self._send_update()
            return
        
        curr_x, curr_y = self._get_curr_pos(key_x, key_y)
        cx, cy = 100, 100
        
        new_x = curr_x + (cx - curr_x) / steps
        new_y = curr_y + (cy - curr_y) / steps
        
        self.angulos_actuales[key_x] = self._map_to_angle(new_x, key_x)
        self.angulos_actuales[key_y] = self._map_to_angle(new_y, key_y)
        
        self._update_canvas(key_x)
        self._send_update()
        
        self.after(20, lambda: self._animate_center(key_x, key_y, steps - 1))

    def _get_curr_pos(self, key_x, key_y):
        def angle_to_pos(angle, eje):
            lims = self.limites[eje]
            if angle < lims["centro"]:
                return 100 * ((angle - lims["min"]) / (lims["centro"] - lims["min"]))
            else:
                return 100 + 100 * ((angle - lims["centro"]) / (lims["max"] - lims["centro"]))
        
        return angle_to_pos(self.angulos_actuales[key_x], key_x), angle_to_pos(self.angulos_actuales[key_y], key_y)

    def _update_canvas(self, key_x):
        obj = self.canvas_objects[key_x]
        x, y = self._get_curr_pos(obj["key_x"], obj["key_y"])
        obj["canvas"].coords(obj["circle"], x-5, y-5, x+5, y+5)
        obj["lbl"].config(text=f"{obj['key_x']}: {self.angulos_actuales[obj['key_x']]}° | {obj['key_y']}: {self.angulos_actuales[obj['key_y']]}°")

    def _send_update(self):
        if self.puente:
            self.puente.set_angulos(
                j1x=self.angulos_actuales["J1X"],
                j1y=self.angulos_actuales["J1Y"],
                j2x=self.angulos_actuales["J2X"],
                j2y=self.angulos_actuales["J2Y"]
            )
            self.master_app.sent_label.config(text=f"Enviado: J1X:{self.angulos_actuales['J1X']};J1Y:{self.angulos_actuales['J1Y']};J2X:{self.angulos_actuales['J2X']};J2Y:{self.angulos_actuales['J2Y']}")

    def _on_profile_change(self, event):
        nuevo_perfil = self.profile_combo.get()
        self.master_app.notificar_cambio_perfil(nuevo_perfil)
        
    def _update_ui_state(self):
        if not self.puente:
            for obj in self.canvas_objects.values():
                obj["canvas"].config(state="disabled")
                obj["canvas"].create_text(100, 100, text="Sin conexión", fill="gray")
