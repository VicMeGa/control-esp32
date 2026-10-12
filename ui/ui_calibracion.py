import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import perfiles

class CalibracionTab(ttk.Frame):
    def __init__(self, parent, puente):
        super().__init__(parent)
        self.puente = puente
        self.master_app = parent.master
        
        self.angulos = self.master_app.angulos_globales
        self.perfil_edicion = self.master_app.perfil_activo
        
        self.canvas_objects = {}
        self.labels = {}
        self._widgets_listos = False
        
        self._build_ui()
        self._widgets_listos = True

    def _build_ui(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_frame, text="Perfil en edición:").pack(side=tk.LEFT)
        self.profile_combo = ttk.Combobox(top_frame, values=perfiles.listar_perfiles(), state="readonly")
        self.profile_combo.set(self.perfil_edicion)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)
        
        ttk.Button(top_frame, text="Nuevo perfil", command=self._nuevo_perfil).pack(side=tk.LEFT, padx=5)

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(pady=10)
        
        self._create_canvas(canvas_frame, "J1X", "J1Y", "Joystick 1")
        self._create_canvas(canvas_frame, "J2X", "J2Y", "Joystick 2")

        save_frame = ttk.Frame(self)
        save_frame.pack(fill=tk.X, pady=10)
        
        for eje in ["J1X", "J1Y", "J2X", "J2Y"]:
            eje_frame = ttk.LabelFrame(save_frame, text=eje)
            eje_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)
            
            ttk.Button(eje_frame, text="Guardar mín", command=lambda e=eje: self._guardar_valor(e, "min")).pack(fill=tk.X)
            ttk.Button(eje_frame, text="Guardar máx", command=lambda e=eje: self._guardar_valor(e, "max")).pack(fill=tk.X)
            ttk.Button(eje_frame, text="Guardar centro", command=lambda e=eje: self._guardar_valor(e, "centro")).pack(fill=tk.X)

    def _create_canvas(self, parent, key_x, key_y, label):
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(frame, text=label).pack()
        canvas = tk.Canvas(frame, width=200, height=200, bg="white", highlightbackground="gray")
        canvas.pack()
        
        cx, cy = 100, 100
        circle = canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill="red")
        
        lbl_x = ttk.Label(frame, text=f"{key_x}: {self.angulos[key_x]}°")
        lbl_x.pack()
        lbl_y = ttk.Label(frame, text=f"{key_y}: {self.angulos[key_y]}°")
        lbl_y.pack()
        
        self.labels[key_x] = lbl_x
        self.labels[key_y] = lbl_y
        
        canvas.bind("<B1-Motion>", lambda event: self._on_canvas_drag(event, key_x, key_y, canvas, circle, lbl_x, lbl_y))

    def _on_canvas_drag(self, event, key_x, key_y, canvas, circle, lbl_x, lbl_y):
        if not self.puente: return
        
        x = max(0, min(event.x, 200))
        y = max(0, min(event.y, 200))
        
        angle_x = int((x / 200) * 180)
        angle_y = int((y / 200) * 180)
        
        self.angulos[key_x] = angle_x
        self.angulos[key_y] = angle_y
        
        canvas.coords(circle, x-5, y-5, x+5, y+5)
        lbl_x.config(text=f"{key_x}: {angle_x}°")
        lbl_y.config(text=f"{key_y}: {angle_y}°")
        
        self._send_update()

    def _send_update(self):
        self.master_app.actualizar_angulos(
            J1X=self.angulos["J1X"],
            J1Y=self.angulos["J1Y"],
            J2X=self.angulos["J2X"],
            J2Y=self.angulos["J2Y"]
        )

    def _guardar_valor(self, eje, campo):
        if not self._widgets_listos: return
        
        try:
            val = self.angulos[eje]
            perfiles.actualizar_valor(self.perfil_edicion, eje, campo, val)
            messagebox.showinfo("Guardado", f"{campo} de {eje} guardado como {val}° en perfil {self.perfil_edicion}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _nuevo_perfil(self):
        nombre = simpledialog.askstring("Nuevo perfil", "Nombre del perfil:")
        if nombre:
            try:
                perfiles.crear_perfil(nombre)
                self.master_app.notificar_cambio_perfil(nombre)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _on_profile_change(self, event):
        nuevo_perfil = self.profile_combo.get()
        self.master_app.notificar_cambio_perfil(nuevo_perfil)
