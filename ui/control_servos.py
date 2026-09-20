import serial
import time

class PuenteServos:
    def __init__(self, port):
        # Simulación de conexión serial
        self.ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2) # Esperar a que el ESP32 reinicie si es necesario

    def set_angulos(self, j1x, j1y, j2x, j2y):
        cmd = f"J1X:{j1x};J1Y:{j1y};J2X:{j2x};J2Y:{j2y}\n"
        self.ser.write(cmd.encode())
        return self.ser.readline().decode().strip()

    def status(self):
        self.ser.write(b"STATUS\n")
        return self.ser.readline().decode().strip()

    def close(self):
        if self.ser.is_open:
            self.ser.close()
