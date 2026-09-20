/*
 * ESP32 - Puente de control de servos para joysticks de mando
 * ==============================================================
 * Framework: ESP-IDF nativo (NO Arduino)
 *
 * Rol: SOLO ejecutor. No guarda calibracion, no aplica limites,
 * no decide nada. Recibe angulos objetivo por consola serial (UART0,
 * la misma que usa "idf.py monitor") desde la PC y mueve los
 * servos correspondientes via PCA9685 (I2C).
 *
 * Toda la logica (calibracion de limites, mapeo, suavizado, etc.)
 * vive en la PC. Este firmware es intencionalmente "tonto".
 *
 * Protocolo serial (115200 baud, terminar cada comando con '\n'):
 * -----------------------------------------------------------------
 * J1X:90;J1Y:45;J2X:120;J2Y:60
 *
 * - Puedes mandar solo los servos que quieras actualizar:
 *     J1X:90
 *     J1Y:150;J2Y:30
 * - Los valores son angulos en grados (0-180), se limitan (clamp)
 *   a ese rango por seguridad mecanica del servo, NO por logica
 *   de joystick.
 * - Respuesta: "OK" tras aplicar el comando, "ERROR" si alguna
 *   clave no se reconocio.
 * - Comando especial "STATUS" devuelve los angulos actuales.
 *
 * Conexion de hardware:
 * -----------------------------------------------------------------
 * - ESP32 <-> PCA9685 por I2C:
 *     ESP32 GPIO 21 (SDA) -> PCA9685 SDA
 *     ESP32 GPIO 22 (SCL) -> PCA9685 SCL
 *     ESP32 3.3V          -> PCA9685 VCC (logica del chip)
 * - PCA9685 V+ (bloque de tornillos, alimentacion de servos)
 *     -> fuente EXTERNA de 5V (NO desde el ESP32 ni USB)
 * - GND: fuente externa, PCA9685 y ESP32 deben compartir tierra.
 * - Servos en los canales:
 *     Joystick1 - Eje X -> Canal 0
 *     Joystick1 - Eje Y -> Canal 1
 *     Joystick2 - Eje X -> Canal 2
 *     Joystick2 - Eje Y -> Canal 3
 *
 * No requiere librerias externas: usa el driver I2C incluido en
 * ESP-IDF (componente "driver").
 */

#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

// ---------- Configuracion I2C ----------
#define I2C_MASTER_NUM      I2C_NUM_0
#define I2C_MASTER_SDA_IO   21
#define I2C_MASTER_SCL_IO   22++++++++
#define I2C_MASTER_FREQ_HZ  400000
#define PCA9685_ADDR        0x40   // direccion default del PCA9685

// ---------- Registros del PCA9685 ----------
#define PCA9685_MODE1       0x00
#define PCA9685_MODE2       0x01
#define PCA9685_PRESCALE    0xFE
#define PCA9685_LED0_ON_L   0x06   // cada canal ocupa 4 registros consecutivos

#define MODE1_SLEEP   0x10
#define MODE1_AUTOINC 0x20
#define MODE1_RESTART 0x80

// ---------- Canales de servo ----------
#define CH_J1X 0
#define CH_J2X 2
#define CH_J1Y 1
#define CH_J2Y 3

#define SERVO_FREQ_HZ   50.0f
#define PULSE_MIN_US    500
#define PULSE_MAX_US    2400

static const char *TAG = "puente_servos";

// Estado actual (solo para responder STATUS)
static int angJ1X = 90, angJ1Y = 90, angJ2X = 90, angJ2Y = 90;

// ================= I2C bajo nivel =================

static esp_err_t i2c_master_init(void) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    esp_err_t err = i2c_param_config(I2C_MASTER_NUM, &conf);
    if (err != ESP_OK) return err;
    return i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
}

// Escanea el bus I2C completo y reporta que direcciones responden.
// Util para confirmar que el PCA9685 esta bien cableado (SDA/SCL/GND)
// ANTES de asumir que el problema es de software.
static void i2c_scan(void) {
    ESP_LOGI(TAG, "Escaneando bus I2C...");
    int encontrados = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        i2c_master_start(cmd);
        i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
        i2c_master_stop(cmd);
        esp_err_t err = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd, pdMS_TO_TICKS(50));
        i2c_cmd_link_delete(cmd);

        if (err == ESP_OK) {
            ESP_LOGI(TAG, "  Dispositivo encontrado en 0x%02X", addr);
            encontrados++;
        }
    }
    if (encontrados == 0) {
        ESP_LOGE(TAG, "  NINGUN dispositivo respondio en el bus I2C.");
        ESP_LOGE(TAG, "  Revisa: SDA->GPIO21, SCL->GPIO22, VCC del PCA9685, GND comun.");
    } else if (encontrados == 1) {
        ESP_LOGI(TAG, "  1 dispositivo encontrado (esperado si es solo el PCA9685).");
    }
}

static esp_err_t pca9685_write8(uint8_t reg, uint8_t value) {
    uint8_t buf[2] = { reg, value };
    esp_err_t err = i2c_master_write_to_device(I2C_MASTER_NUM, PCA9685_ADDR,
                                                buf, sizeof(buf),
                                                pdMS_TO_TICKS(100));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Fallo escritura I2C reg 0x%02X: %s", reg, esp_err_to_name(err));
    }
    return err;
}

static esp_err_t pca9685_read8(uint8_t reg, uint8_t *value) {
    return i2c_master_write_read_device(I2C_MASTER_NUM, PCA9685_ADDR,
                                         &reg, 1, value, 1,
                                         pdMS_TO_TICKS(100));
}

// ================= PCA9685 alto nivel =================

static void pca9685_reset(void) {
    // Escribe MODE1 = 0x00: saca al chip de sleep (oscilador arranca),
    // sin AllCall ni restart todavia. Esto es indispensable antes de
    // configurar el prescaler, o el chip puede quedarse dormido para
    // siempre y nunca sacar PWM real por los pines.
    pca9685_write8(PCA9685_MODE1, 0x00);
    vTaskDelay(pdMS_TO_TICKS(10));
}

static void pca9685_set_pwm_freq(float freq_hz) {
    float prescaleval = 25000000.0f;  // oscilador interno del PCA9685
    prescaleval /= 4096.0f;
    prescaleval /= freq_hz;
    prescaleval -= 1.0f;
    uint8_t prescale = (uint8_t)(floorf(prescaleval + 0.5f));

    uint8_t oldmode;
    pca9685_read8(PCA9685_MODE1, &oldmode);
    uint8_t sleepmode = (oldmode & 0x7F) | MODE1_SLEEP;

    pca9685_write8(PCA9685_MODE1, sleepmode);       // entrar a sleep para poder cambiar prescale
    pca9685_write8(PCA9685_PRESCALE, prescale);
    pca9685_write8(PCA9685_MODE1, oldmode);
    vTaskDelay(pdMS_TO_TICKS(5));
    pca9685_write8(PCA9685_MODE1, oldmode | MODE1_RESTART | MODE1_AUTOINC);
}

static void pca9685_set_pwm(uint8_t channel, uint16_t on, uint16_t off) {
    uint8_t reg = PCA9685_LED0_ON_L + 4 * channel;
    uint8_t buf[5] = {
        reg,
        (uint8_t)(on & 0xFF),
        (uint8_t)(on >> 8),
        (uint8_t)(off & 0xFF),
        (uint8_t)(off >> 8)
    };
    esp_err_t err = i2c_master_write_to_device(I2C_MASTER_NUM, PCA9685_ADDR,
                                                buf, sizeof(buf), pdMS_TO_TICKS(100));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Fallo set_pwm canal %d: %s", channel, esp_err_to_name(err));
    }
}

// Convierte angulo (0-180) a ticks (0-4095) y lo manda al canal
static void mover_servo(uint8_t canal, int angulo) {
    if (angulo < 0) angulo = 0;
    if (angulo > 180) angulo = 180;

    int pulso_us = PULSE_MIN_US +
        (int)((PULSE_MAX_US - PULSE_MIN_US) * (angulo / 180.0f));

    int ticks = (int)((pulso_us * 4096.0f) / (1000000.0f / SERVO_FREQ_HZ));
    if (ticks > 4095) ticks = 4095;

    pca9685_set_pwm(canal, 0, (uint16_t)ticks);
}

// ================= Parser de comandos =================

static bool aplicar_par(char *par) {
    char *dos_puntos = strchr(par, ':');
    if (!dos_puntos) return false;

    *dos_puntos = '\0';
    char *clave = par;
    int valor = atoi(dos_puntos + 1);
    if (valor < 0) valor = 0;
    if (valor > 180) valor = 180;

    if (strcasecmp(clave, "J1X") == 0) {
        angJ1X = valor; mover_servo(CH_J1X, valor);
    } else if (strcasecmp(clave, "J1Y") == 0) {
        angJ1Y = valor; mover_servo(CH_J1Y, valor);
    } else if (strcasecmp(clave, "J2X") == 0) {
        angJ2X = valor; mover_servo(CH_J2X, valor);
    } else if (strcasecmp(clave, "J2Y") == 0) {
        angJ2Y = valor; mover_servo(CH_J2Y, valor);
    } else {
        return false;
    }
    return true;
}

static void enviar_status(void) {
    printf("J1X:%d,J1Y:%d,J2X:%d,J2Y:%d\n", angJ1X, angJ1Y, angJ2X, angJ2Y);
}

static void procesar_linea(char *linea) {
    // quitar salto de linea / retorno de carro al final
    linea[strcspn(linea, "\r\n")] = '\0';

    if (strlen(linea) == 0) return;

    if (strcasecmp(linea, "STATUS") == 0) {
        enviar_status();
        return;
    }

    bool hubo_error = false;
    char *token = strtok(linea, ";");
    while (token != NULL) {
        // saltar espacios al inicio
        while (isspace((unsigned char)*token)) token++;
        if (strlen(token) > 0) {
            if (!aplicar_par(token)) hubo_error = true;
        }
        token = strtok(NULL, ";");
    }

    printf(hubo_error ? "ERROR\n" : "OK\n");
}

// ================= Tarea principal de lectura serial =================

static void tarea_serial(void *arg) {
    char linea[128];

    while (1) {
        if (fgets(linea, sizeof(linea), stdin) != NULL) {
            procesar_linea(linea);
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Inicializando I2C y PCA9685...");
    ESP_ERROR_CHECK(i2c_master_init());

    i2c_scan();

    uint8_t mode1_antes = 0xFF, mode1_despues = 0xFF;
    pca9685_read8(PCA9685_MODE1, &mode1_antes);
    ESP_LOGI(TAG, "MODE1 antes del reset: 0x%02X", mode1_antes);

    pca9685_reset();
    pca9685_set_pwm_freq(SERVO_FREQ_HZ);

    pca9685_read8(PCA9685_MODE1, &mode1_despues);
    ESP_LOGI(TAG, "MODE1 despues de configurar: 0x%02X (bit SLEEP=%d)",
             mode1_despues, (mode1_despues >> 4) & 0x01);
    vTaskDelay(pdMS_TO_TICKS(10));

    // Posicion inicial: centro (90 grados) en los 4 servos
    mover_servo(CH_J1X, angJ1X);
    mover_servo(CH_J1Y, angJ1Y);
    mover_servo(CH_J2X, angJ2X);
    mover_servo(CH_J2Y, angJ2Y);

    printf("READY\n");

    xTaskCreate(tarea_serial, "tarea_serial", 4096, NULL, 5, NULL);
}