import tkinter as tk
from tkinter import ttk, messagebox
import queue
import perfiles
import serial.tools.list_ports
from serial_bridge import PuenteServos
from ui_control import ControlTab
from ui_calibracion import CalibracionTab
from ui_resumen import ResumenTab
from ui_individual import IndividualTab

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control de Servos ESP32")
        self.geometry("800x550")
        
        self.puente = None
        self.perfil_activo = perfiles.obtener_perfil_activo()
        
        self._setup_top_bar()
        self._setup_notebook()
        self._setup_bottom_bar()
        
        self.after(50, self.process_queue)

    def _setup_top_bar(self):
        frame = ttk.Frame(self, padding=5)
        frame.pack(fill=tk.X, side=tk.TOP)
        
        ttk.Label(frame, text="Puerto:").pack(side=tk.LEFT)
        
        # Combobox editable para puertos
        self.port_combo = ttk.Combobox(frame, width=20, state="normal")
        self.port_combo.pack(side=tk.LEFT, padx=5)
        self.port_combo.bind("<Button-1>", self._refresh_ports)
        self._refresh_ports()
        
        self.conn_btn = ttk.Button(frame, text="Conectar", command=self.toggle_connection)
        self.conn_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(frame, text="Desconectado", fg="red")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.error_test_btn = ttk.Button(frame, text="Enviar inválido (test)", command=self._send_invalid_test)
        self.error_test_btn.pack(side=tk.LEFT, padx=5)

    def _refresh_ports(self, event=None):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports

    def _setup_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        self.tab_classes = [ControlTab, CalibracionTab, ResumenTab, IndividualTab]
        self.tab_names = ["Control", "Calibración", "Resumen", "Individual"]
        self.tabs = {}
        
        for tab_class, nombre in zip(self.tab_classes, self.tab_names):
            instancia = tab_class(self.notebook, None)
            self.notebook.add(instancia, text=nombre)
            self.tabs[nombre] = instancia

    def _setup_bottom_bar(self):
        frame = ttk.Frame(self, padding=5)
        frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.sent_label = ttk.Label(frame, text="Enviado: -")
        self.sent_label.pack(side=tk.LEFT, padx=5)
        
        self.resp_label = ttk.Label(frame, text="Respuesta: -")
        self.resp_label.pack(side=tk.LEFT, padx=20)

    def _send_invalid_test(self):
        puente_actual = self.puente
        if puente_actual:
            puente_actual.ser.write(b"BASURA_TEST\n")

    def notificar_cambio_perfil(self, nuevo_nombre):
        self.perfil_activo = nuevo_nombre
        perfiles.establecer_perfil_activo(nuevo_nombre)
        self._reinit_tabs()

    def toggle_connection(self):
        if self.puente is None: self.conectar()
        else: self.desconectar()

    def conectar(self):
        port = self.port_combo.get()
        if not port:
            messagebox.showerror("Error", "Selecciona o escribe un puerto")
            return
        try:
            self.puente = PuenteServos(port)
            self.status_label.config(text="Conectado", fg="green")
            self.conn_btn.config(text="Desconectar")
            self._reinit_tabs()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def desconectar(self):
        if self.puente:
            self.puente.close()
            self.puente = None
            self.status_label.config(text="Desconectado", fg="red")
            self.conn_btn.config(text="Conectar")
            self._reinit_tabs()

    def _reinit_tabs(self):
        tabs_viejas = list(self.notebook.tabs())
        # Captura puente_actual para pasar a pestañas
        puente_actual = self.puente
        nuevas_instancias = [tab_class(self.notebook, puente_actual) for tab_class in self.tab_classes]
        
        for tab_id in tabs_viejas: self.notebook.forget(tab_id)
        for nombre, instancia in zip(self.tab_names, nuevas_instancias):
            self.notebook.add(instancia, text=nombre)
        self.tabs = dict(zip(self.tab_names, nuevas_instancias))

    def process_queue(self):
        puente_actual = self.puente
        if puente_actual is not None:
            try:
                while True:
                    msg = puente_actual.recv_queue.get_nowait()
                    if msg == "DESCONECTADO":
                        self.desconectar()
                        messagebox.showwarning("Aviso", "Conexión perdida")
                    else:
                        color = "red" if msg == "ERROR" else "black"
                        self.resp_label.config(text=f"Respuesta: {msg}", foreground=color)
            except queue.Empty: pass
        self.after(50, self.process_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()
