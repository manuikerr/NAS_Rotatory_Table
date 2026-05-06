import serial
import time
import random
import os
from datetime import datetime
import threading

# --- CONFIGURACIÓN ---
PUERTO_SERIE = 'COMX'
BAUD_RATE = 115200
DURACION_HORAS = 0.5
SEGUNDOS_TOTALES = DURACION_HORAS * 3600
ESPERA_CONSTANTE = 5.0

# --- VARIABLES GLOBALES DE CONTROL
entrenando = False
hilo_entrenamiento = None

# velocidad -> MaxSpd_Steps_to_Par
# aceleracion -> AccDec_Steps_to_Par
# desaceleracion -> AccDec_Steps_to_Par
# angulo -> K_ANG
def enviar_comando_dinamico(conexion, velocidad, aceleracion, desaceleracion, angulo, log_file):
    # Formato: V:500.0,A:1000.0,D:1000.0,G:90.0\n
    comando = f"V:{velocidad:.1f},A:{aceleracion:.1f},D:{desaceleracion:.1f},G:{angulo:.2f}\n"
    conexion.write(comando.encode('utf-8'))

    respuesta_cruda = conexion.readline()
    respuesta_stm = respuesta_cruda.decode('utf-8').strip()
    
    if respuesta_stm == "":
        respuesta_stm = "TIMEOUT (Sin respuesta del STM32)"
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    info = f"[{timestamp}] Ang:{angulo:>6.1f}º | Vel:{velocidad:>5.0f} | Acc:{aceleracion:>5.0f} | Dec:{desaceleracion:>5.0f} --> [STM32]: {respuesta_stm}"
    
    print(f"-> {info}")
    log_file.write(info + "\n")
    log_file.flush()

# Función aux que se ejecuta al iniciar el entrenamiento
def rutina_entrenamiento(conexion, log_file):
    global entrenando
    print("\n[✔] Iniciando entrenamiento...")
    log_file.write(f"\n--- Inicio de sesión de entrenamiento: {datetime.now()} ---\n")
    
    inicio_test = time.time()
    fin_test = inicio_test + SEGUNDOS_TOTALES

    while entrenando and time.time() < fin_test:
        # Parámetros aleatorios
        ang_rand = random.uniform(-180.0, 180.0)
        vel_rand = random.uniform(200.0, 800.0)
        acc_rand = random.uniform(800.0, 4000.0)
        dec_rand = random.uniform(800.0, 4000.0)
        
        enviar_comando_dinamico(conexion, vel_rand, acc_rand, dec_rand, ang_rand, log_file)
        
        # Espera fraccionada para poder interrumpir inmediatamente con 'f' (FINISH)
        pasos_espera = int(ESPERA_CONSTANTE * 10)
        for _ in range(pasos_espera):
            if not entrenando:
                break
            time.sleep(0.1)
            
    if entrenando:
        print("\n[✔] Entrenamiento finalizado automáticamente por tiempo.")
        log_file.write(f"\n--- Fin de sesión por tiempo: {datetime.now()} ---\n")
        entrenando = False

# TODO: comunicacion entre stm y script (mensajes de ok, recibir, y angulo)
def main():

    global entrenando, hilo_entrenamiento
    
    # 1. Verificar y crear carpeta logs
    if not os.path.exists("logs"):
        try:
            os.makedirs("logs")
        except Exception:
            print("[!] Error: No se pudo crear la carpeta 'logs'.")
            return

    # 2. Conexión Serial
    print("[...] Conectando con el motor...")
    try:
        conexion = serial.Serial(PUERTO_SERIE, BAUD_RATE, timeout=1.0)
        time.sleep(2)
        print("[✔] ¡Conexión establecida!")
    except serial.SerialException as e:
        print(f"[!] Error de puerto serie: {e}")
        return
    
    nombre_log = f"log_entrenamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    ruta_log = os.path.join("logs", nombre_log)
    print(f"[✔] Log guardándose en: {ruta_log}")

    try:
        with open(ruta_log, "a") as log_file:
            #TODO: --- MÁQUINA DE ESTADOS---
            while True:
                comando_usuario = input("\nEsperando comando (h: homing, s: start, f: finish, q: quit)...: ").strip().lower()
                
                if comando_usuario == 'h':
                    if entrenando:
                        print("[!] Error: Detén el entrenamiento con 'f'(FINISH) antes de hacer Homing.")
                    else:

                        conexion.timeout = 12.0 # le damos tiempo al motor para el homing

                        print("[...] Iniciando Homing...")
                        conexion.write(b"HOME\n")
                        
                        print("[...] Esperando a que el STM32 complete la rutina de Homing...")
                        respuesta_cruda = conexion.readline()
                        respuesta_stm = respuesta_cruda.decode('utf-8').strip()

                        conexion.timeout = 1.0 # volvemos a 1 para la rutina de entrenamiento
                        
                        if "Homing completado" in respuesta_stm:
                            print(f"[✔] [STM32]: {respuesta_stm}. ¡Cero lógico establecido con éxito!")
                            log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Calibración exitosa: {respuesta_stm}\n")
                        else:
                            print(f"[!] [STM32] Respuesta inesperada durante el homing: {respuesta_stm}")
                            log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Alerta en Homing: {respuesta_stm}\n")
                            
                        log_file.flush()

                elif comando_usuario == 's':
                    if not entrenando:
                        entrenando = True
                        # Lanzamos la rutina de entrenamiento en un hilo separado
                        hilo_entrenamiento = threading.Thread(target=rutina_entrenamiento, args=(conexion, log_file))
                        hilo_entrenamiento.start()
                    else:
                        print("[!] El entrenamiento ya está en marcha.")

                elif comando_usuario == 'f':
                    if entrenando:
                        print("[...] Finalizando entrenamiento de forma segura...")
                        entrenando = False
                        hilo_entrenamiento.join() # Espera a que el hilo secundario termine limpiamente
                        print("[✔] Entrenamiento detenido.")
                        log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Entrenamiento abortado por el usuario.\n")
                        log_file.flush()
                    else:
                        print("[!] No hay ningún entrenamiento activo que detener.")

                elif comando_usuario == 'q':
                    print("[...] Saliendo del programa...")
                    if entrenando:
                        entrenando = False
                        hilo_entrenamiento.join()
                    break
                    
                else:
                    print("[!] Comando no reconocido. Usa 'h' (HOME), 's' (START), 'f' (FINISH) o 'q' (QUIT).")
    except KeyboardInterrupt:
        print("\n[!] Interrumpido (Ctrl + C).")
        if entrenando:
            entrenando = False
            hilo_entrenamiento.join()
    finally:
        conexion.close()
        print("[✔] Puerto serie cerrado y asegurado.")

if __name__ == "__main__":
    main()