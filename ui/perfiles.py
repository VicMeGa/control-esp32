import json
import os
import copy

PERFILES_FILE = "perfiles.json"

DEFAULT_DATA = {
    "perfil_activo": "default",
    "perfiles": {
        "default": {
            "J1X": {"min": 0, "centro": 90, "max": 180},
            "J1Y": {"min": 0, "centro": 90, "max": 180},
            "J2X": {"min": 0, "centro": 90, "max": 180},
            "J2Y": {"min": 0, "centro": 90, "max": 180}
        }
    }
}

def cargar():
    if not os.path.exists(PERFILES_FILE):
        guardar(DEFAULT_DATA)
        return copy.deepcopy(DEFAULT_DATA)
    with open(PERFILES_FILE, "r") as f:
        data = json.load(f)
        return copy.deepcopy(data)

def guardar(datos):
    with open(PERFILES_FILE, "w") as f:
        json.dump(datos, f, indent=2)

def listar_perfiles():
    return list(cargar()["perfiles"].keys())

def crear_perfil(nombre):
    datos = cargar()
    if nombre in datos["perfiles"]:
        raise ValueError(f"El perfil '{nombre}' ya existe.")
    datos["perfiles"][nombre] = copy.deepcopy(DEFAULT_DATA["perfiles"]["default"])
    guardar(datos)

def obtener_perfil(nombre):
    datos = cargar()
    if nombre not in datos["perfiles"]:
        raise ValueError(f"El perfil '{nombre}' no existe.")
    return datos["perfiles"][nombre]

def actualizar_valor(nombre_perfil, eje, campo, valor):
    if not (0 <= valor <= 180):
        raise ValueError("El valor debe estar entre 0 y 180.")
    if eje not in ["J1X", "J1Y", "J2X", "J2Y"]:
        raise ValueError("Eje inválido.")
    if campo not in ["min", "centro", "max"]:
        raise ValueError("Campo inválido.")
    
    datos = cargar()
    if nombre_perfil not in datos["perfiles"]:
        raise ValueError(f"El perfil '{nombre_perfil}' no existe.")
    
    datos["perfiles"][nombre_perfil][eje][campo] = valor
    guardar(datos)

def obtener_perfil_activo():
    return cargar()["perfil_activo"]

def establecer_perfil_activo(nombre):
    datos = cargar()
    if nombre not in datos["perfiles"]:
        raise ValueError(f"El perfil '{nombre}' no existe.")
    datos["perfil_activo"] = nombre
    guardar(datos)

if __name__ == "__main__":
    # Test manual
    TEST_NOMBRE = "test_fase4"
    
    print("--- Iniciando pruebas de perfiles.py ---")
    
    # 1. Crear y actualizar
    if TEST_NOMBRE in listar_perfiles():
        # Limpieza previa si existiera por una ejecución fallida
        d = cargar()
        del d["perfiles"][TEST_NOMBRE]
        guardar(d)
        
    crear_perfil(TEST_NOMBRE)
    actualizar_valor(TEST_NOMBRE, "J1X", "min", 15)
    
    # 2. Recargar y verificar
    datos_recargados = cargar()
    valor = datos_recargados["perfiles"][TEST_NOMBRE]["J1X"]["min"]
    
    print(f"Valor leído tras guardar: {valor}")
    assert valor == 15, "Error: El valor no persiste correctamente."
    print("Prueba exitosa: El valor persiste en disco.")
    
    # 3. Limpieza
    d = cargar()
    del d["perfiles"][TEST_NOMBRE]
    guardar(d)
    print("--- Pruebas finalizadas y limpieza realizada ---")
