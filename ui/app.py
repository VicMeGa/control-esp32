import tkinter as tk
from tkinter import ttk, messagebox
import queue
from serial_bridge import PuenteServos
from ui_control import ControlTab
from ui_calibracion import CalibracionTab
from ui_resumen import ResumenTab
from ui_individual import IndividualTab

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control de Servos ESP32")
        self.geometry("700x450")
        
        self.puente = None
        self.is_testing = False
        
        self._setup_top_bar()
        self._setup_notebook()
        
        # Iniciar loop de procesamiento de cola
        self.after(50, self.process_queue)

    def _setup_top_bar(self):
        # Frame principal para la barra superior
        frame = ttk.Frame(self, padding=5)
        frame.pack(fill=tk.X, side=tk.TOP)
        
        # Puerto serial
        ttk.Label(frame, text="Puerto:").pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(frame, width=15)
        self.port_entry.insert(0, "/dev/ttyUSB0")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Botón Conectar/Desconectar
        self.conn_btn = ttk.Button(frame, text="Conectar", command=self.toggle_connection)
        self.conn_btn.pack(side=tk.LEFT, padx=5)
        
        # Estado
        self.status_label = tk.Label(frame, text="Desconectado", fg="red")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Botón de Test (Fase 2)
        self.test_btn = ttk.Button(frame, text="Test (Mantener)")
        self.test_btn.pack(side=tk.LEFT, padx=5)
        self.test_btn.bind("<ButtonPress-1>", self.start_test)
        self.test_btn.bind("<ButtonRelease-1>", self.stop_test)
        
        # Debug
        self.debug_label = ttk.Label(frame, text="", foreground="blue")
        self.debug_label.pack(side=tk.LEFT, padx=10)

    def _setup_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        self.tabs = {}
        self.tab_classes = [ControlTab, CalibracionTab, ResumenTab, IndividualTab]
        self.tab_names = ["Control", "Calibración", "Resumen", "Individual"]
        
        for i, tab_class in enumerate(self.tab_classes):
            tab = tab_class(self.notebook, None)
            self.notebook.add(tab, text=self.tab_names[i])
            self.tabs[self.tab_names[i]] = tab

    def toggle_connection(self):
        if self.puente is None:
            self.conectar()
        else:
            self.desconectar()

    def conectar(self):
        port = self.port_entry.get()
        try:
            self.puente = PuenteServos(port)
            self.status_label.config(text="Conectado", fg="green")
            self.conn_btn.config(text="Desconectar")
            self._reinit_tabs()
        except Exception as e:
            messagebox.showerror("Error de Conexión", str(e))

    def desconectar(self):
        if self.puente:
            self.puente.close()
            self.puente = None
            self.status_label.config(text="Desconectado", fg="red")
            self.conn_btn.config(text="Conectar")
            self.debug_label.config(text="")
            self._reinit_tabs()

    def _reinit_tabs(self):
        # Limpiar y recrear pestañas para pasar la nueva instancia de puente
        for i, tab_class in enumerate(self.tab_classes):
            tab = self.notebook.tabs()[i]
            self.notebook.forget(tab)
            new_tab = tab_class(self.notebook, self.puente)
            self.notebook.add(new_tab, text=self.tab_names[i])

    def process_queue(self):
        if self.puente:
            try:
                while True:
                    msg = self.puente.recv_queue.get_nowait()
                    if msg == "DESCONECTADO":
                        self.desconectar()
                        messagebox.showwarning("Aviso", "Conexión perdida")
                    else:
                        self.debug_label.config(text=f"Recibido: {msg}")
            except queue.Empty:
                pass
        self.after(50, self.process_queue)

    def start_test(self, event):
        if self.puente:
            self.is_testing = True
            self.run_test_command()

    def stop_test(self, event):
        self.is_testing = False

    def run_test_command(self):
        if self.is_testing and self.puente:
            self.puente.set_angulos(90, 90, 90, 90)
            self.after(200, self.run_test_command)

if __name__ == "__main__":
    app = App()
    app.mainloop()
