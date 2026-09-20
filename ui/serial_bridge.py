import serial
import threading
import queue
import time

class PuenteServos:
    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout=0.1)
        self._running = threading.Event()
        self._running.set()
        self.recv_queue = queue.Queue()
        
        # Mecanismos de comandos
        self._command_queue = queue.Queue() # FIFO para comandos de consulta (STATUS)
        self._pending_movement = None      # Último comando de movimiento (last-one-wins)
        self._lock = threading.Lock()
        
        # Iniciar hilo de trabajo
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def set_angulos(self, j1x, j1y, j2x, j2y):
        cmd = f"J1X:{j1x};J1Y:{j1y};J2X:{j2x};J2Y:{j2y}\n"
        with self._lock:
            self._pending_movement = cmd

    def status(self):
        self._command_queue.put("STATUS\n")

    def _worker(self):
        # --- CORRECCIÓN: Tiempo de espera y limpieza del buffer en el hilo secundario ---
        # Esto permite que el GUI no se congele durante el arranque del ESP32
        time.sleep(2.0)
        self.ser.reset_input_buffer()
        # -------------------------------------------------------------------------------
        
        last_activity = time.time()
        while self._running.is_set():
            # 1. Enviar (Prioridad a _command_queue, luego _pending_movement)
            cmd_to_send = None
            
            # Prioridad 1: Comandos de consulta
            try:
                cmd_to_send = self._command_queue.get_nowait()
            except queue.Empty:
                # Prioridad 2: Movimientos (sobrescritos)
                with self._lock:
                    if self._pending_movement:
                        cmd_to_send = self._pending_movement
                        self._pending_movement = None
            
            # Heartbeat si no hubo actividad en 1 segundo
            if not cmd_to_send and (time.time() - last_activity) > 1.0:
                cmd_to_send = "STATUS\n"
            
            if cmd_to_send:
                try:
                    self.ser.write(cmd_to_send.encode())
                    last_activity = time.time()
                except (serial.SerialException, OSError):
                    self._notify_disconnection()
                    break
            
            # 2. Leer
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    if line:
                        self.recv_queue.put(line)
                        last_activity = time.time()
            except (serial.SerialException, OSError):
                self._notify_disconnection()
                break
            
            time.sleep(0.01) # Pequeña pausa para no saturar CPU

    def _notify_disconnection(self):
        self.recv_queue.put("DESCONECTADO")
        self._running.clear()

    def close(self):
        self._running.clear()
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.ser.is_open:
            self.ser.close()
