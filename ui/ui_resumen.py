import tkinter as tk
from tkinter import ttk, messagebox
import perfiles

class ResumenTab(ttk.Frame):
    def __init__(self, parent, puente):
        super().__init__(parent)
        self.puente = puente
        self.master_app = parent.master
        
        self.perfil_actual = self.master_app.perfil_activo
        self.entries = {} # {eje: {campo: Entry}}
        
        self._build_ui()
        self._load_profile_data()

    def _build_ui(self):
        # 1. Selector de perfil
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_frame, text="Perfil:").pack(side=tk.LEFT)
        self.profile_combo = ttk.Combobox(top_frame, values=perfiles.listar_perfiles(), state="readonly")
        self.profile_combo.set(self.perfil_actual)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)
        
        ttk.Button(top_frame, text="Recargar", command=self._load_profile_data).pack(side=tk.LEFT, padx=5)

        # 2. Tabla (Grid de Entry)
        table_frame = ttk.Frame(self)
        table_frame.pack(pady=10)
        
        # Cabeceras
        for i, campo in enumerate(["Min", "Centro", "Max"]):
            ttk.Label(table_frame, text=campo).grid(row=0, column=i+1, padx=5)
        
        # Filas
        for row_idx, eje in enumerate(["J1X", "J1Y", "J2X", "J2Y"]):
            ttk.Label(table_frame, text=eje).grid(row=row_idx+1, column=0, padx=5)
            self.entries[eje] = {}
            for col_idx, campo in enumerate(["min", "centro", "max"]):
                entry = ttk.Entry(table_frame, width=10)
                entry.grid(row=row_idx+1, column=col_idx+1, padx=2, pady=2)
                self.entries[eje][campo] = entry

        # 3. Botón Guardar
        ttk.Button(self, text="Guardar cambios al perfil", command=self._save_changes).pack(pady=10)

    def _load_profile_data(self, event=None):
        perfil = self.profile_combo.get()
        if not perfil: return
        
        try:
            datos = perfiles.obtener_perfil(perfil)
            for eje in self.entries:
                for campo in self.entries[eje]:
                    val = datos[eje][campo]
                    self.entries[eje][campo].delete(0, tk.END)
                    self.entries[eje][campo].insert(0, str(val))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el perfil: {e}")

    def _on_profile_change(self, event):
        nuevo_perfil = self.profile_combo.get()
        self.master_app.notificar_cambio_perfil(nuevo_perfil)
        
    def _save_changes(self):
        perfil = self.profile_combo.get()
        nuevos_datos = {}
        
        try:
            for eje in ["J1X", "J1Y", "J2X", "J2Y"]:
                nuevos_datos[eje] = {}
                valores = {}
                for campo in ["min", "centro", "max"]:
                    val_str = self.entries[eje][campo].get()
                    if not val_str.isdigit():
                        raise ValueError(f"{eje} {campo}: Debe ser un número entero.")
                    val = int(val_str)
                    if not (0 <= val <= 180):
                        raise ValueError(f"{eje} {campo}: Debe estar entre 0 y 180.")
                    valores[campo] = val
                    nuevos_datos[eje][campo] = val
                
                if not (valores["min"] < valores["centro"] < valores["max"]):
                    raise ValueError(f"{eje}: Debe cumplir min < centro < max.")
            
            perfiles.guardar_perfil_datos(perfil, nuevos_datos)
            messagebox.showinfo("Guardado", "Cambios guardados exitosamente.")
            
        except ValueError as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
