"""
Control de servos (joysticks) desde la PC via serial
======================================================
Se comunica con el ESP32 (puente PCA9685) usando el protocolo:

    J1X:90;J1Y:45;J2X:120;J2Y:60

La PC es el "cerebro": aqui es donde eventualmente vivira la
calibracion de limites, el mapeo y la logica de control. Por ahora,
en Fase 1, este script solo permite mandar comandos manuales para
probar que los 4 servos respondan correctamente.

Requiere: pyserial
    pip install pyserial
    (o en NixOS: nix-shell -p python3Packages.pyserial)

Uso:
    python control_servos.py --port /dev/ttyUSB0
"""

import argparse
import sys
import time

import serial


class PuenteServos:
    """Wrapper simple sobre el puerto serial hacia el ESP32."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        # dar tiempo al ESP32 para reiniciar tras abrir el puerto
        # (al abrir el puerto serial, muchas placas hacen reset por DTR)
        time.sleep(2.0)
        self.ser.reset_input_buffer()

    def close(self):
        self.ser.close()

    def _enviar(self, comando: str) -> str:
        """Manda una linea de comando y devuelve la respuesta cruda."""
        self.ser.write((comando + "\n").encode("utf-8"))
        respuesta = self.ser.readline().decode("utf-8", errors="replace").strip()
        return respuesta

    def set_angulos(self, j1x=None, j1y=None, j2x=None, j2y=None) -> str:
        """Manda solo los ejes que no sean None. Angulos en grados 0-180."""
        partes = []
        if j1x is not None:
            partes.append(f"J1X:{int(j1x)}")
        if j1y is not None:
            partes.append(f"J1Y:{int(j1y)}")
        if j2x is not None:
            partes.append(f"J2X:{int(j2x)}")
        if j2y is not None:
            partes.append(f"J2Y:{int(j2y)}")

        if not partes:
            return "NADA_QUE_ENVIAR"

        comando = ";".join(partes)
        return self._enviar(comando)

    def status(self) -> dict:
        """Pide el estado actual y lo devuelve como diccionario."""
        respuesta = self._enviar("STATUS")
        estado = {}
        try:
            for par in respuesta.split(","):
                clave, valor = par.split(":")
                estado[clave.strip()] = int(valor.strip())
        except ValueError:
            print(f"[!] Respuesta inesperada de STATUS: {respuesta!r}")
        return estado


def modo_interactivo(puente: PuenteServos):
    print("\nModo interactivo. Comandos disponibles:")
    print("  j1x <angulo>   -> mover joystick1 eje X (0-180)")
    print("  j1y <angulo>   -> mover joystick1 eje Y (0-180)")
    print("  j2x <angulo>   -> mover joystick2 eje X (0-180)")
    print("  j2y <angulo>   -> mover joystick2 eje Y (0-180)")
    print("  centro         -> mandar los 4 servos a 90 grados")
    print("  status         -> pedir angulos actuales")
    print("  salir          -> terminar\n")

    while True:
        try:
            entrada = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not entrada:
            continue

        partes = entrada.split()
        cmd = partes[0].lower()

        if cmd == "salir":
            break

        elif cmd == "centro":
            resp = puente.set_angulos(j1x=90, j1y=90, j2x=90, j2y=90)
            print(f"<< {resp}")

        elif cmd == "status":
            estado = puente.status()
            print(f"<< {estado}")

        elif cmd in ("j1x", "j1y", "j2x", "j2y"):
            if len(partes) < 2:
                print("[!] Falta el angulo. Ejemplo: j1x 90")
                continue
            try:
                angulo = int(partes[1])
            except ValueError:
                print("[!] El angulo debe ser un numero entero.")
                continue

            kwargs = {cmd: angulo}
            resp = puente.set_angulos(**kwargs)
            print(f"<< {resp}")

        else:
            print(f"[!] Comando desconocido: {cmd}")


def prueba_barrido(puente: PuenteServos):
    """Mueve cada servo de 0 a 180 y de regreso, uno a la vez.
    Util para verificar cableado y que cada eje responda solo
    al comando que le corresponde."""
    ejes = ["j1x", "j1y", "j2x", "j2y"]

    for eje in ejes:
        print(f"\nProbando {eje}...")
        for angulo in (0, 45, 90, 135, 180, 90):
            resp = puente.set_angulos(**{eje: angulo})
            print(f"  {eje} -> {angulo} grados | respuesta: {resp}")
            time.sleep(0.6)


def main():
    parser = argparse.ArgumentParser(description="Control de servos via ESP32 puente")
    parser.add_argument("--port", required=True, help="Puerto serial, ej. /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate (default 115200)")
    parser.add_argument(
        "--barrido", action="store_true",
        help="Correr prueba de barrido automatico en vez de modo interactivo"
    )
    args = parser.parse_args()

    print(f"Conectando a {args.port} @ {args.baud} baud...")
    try:
        puente = PuenteServos(args.port, args.baud)
    except serial.SerialException as e:
        print(f"[!] No se pudo abrir el puerto: {e}")
        sys.exit(1)

    print("Conectado.")

    try:
        if args.barrido:
            prueba_barrido(puente)
        else:
            modo_interactivo(puente)
    finally:
        puente.close()
        print("Puerto cerrado.")


if __name__ == "__main__":
    main()