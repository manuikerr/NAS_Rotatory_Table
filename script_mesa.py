import serial
import time
import random
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
PUERTO_SERIE = 'COMX'
BAUD_RATE = 9600
DURACION_HORAS = 0.5
SEGUNDOS_TOTALES = DURACION_HORAS * 3600
ESPERA_CONSTANTE = 5.0

# velocidad -> MaxSpd_Steps_to_Par
# aceleracion -> AccDec_Steps_to_Par
# angulo -> K_ANG
def enviar_comando_dinamico(conexion, velocidad, aceleracion, angulo, log_file):
    # Formato: V:500.0,A:1000.0,G:90.0\n
    comando = f"V:{velocidad:.1f},A:{aceleracion:.1f},G:{angulo:.2f}\n"
    conexion.write(comando.encode('utf-8'))
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    info = f"[{timestamp}] Ang:{angulo:>6.1f}º | Vel:{velocidad:>5.0f} | Acc:{aceleracion:>5.0f}"
    
    print(f"-> {info}")
    log_file.write(info + "\n")
    time.sleep(ESPERA_CONSTANTE)

def main():
    nombre_log = f"log_entrenamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    ruta_log = os.path.join("logs", nombre_log)

    try:
        with serial.Serial(PUERTO_SERIE, BAUD_RATE) as conexion, open(nombre_log, "w") as log_file: # añadiremos timeout si queremos que el stm32 conteste.
            print(f"Log guardándose en: {ruta_log}")
            log_file.write(f"Inicio de entrenamiento: {datetime.now()}\n\n")
            
            time.sleep(2) # Espera conexión
            
            # --- forzamos vuelta al cero al volver a empezar la rutina ---
            print("Calibrando posición inicial (GOTO 0)...")
            enviar_comando_dinamico(conexion, 300, 1000, 0.0, log_file)
            
            inicio_test = time.time()
            fin_test = inicio_test + SEGUNDOS_TOTALES

            while time.time() < fin_test:
                # Parámetros aleatorios
                ang_rand = random.uniform(-180.0, 180.0)
                vel_rand = random.uniform(200.0, 800.0)
                acc_rand = random.uniform(800.0, 4000.0)
                
                enviar_comando_dinamico(conexion, vel_rand, acc_rand, ang_rand, log_file)

    except serial.SerialException as e:
        print(f"Error de puerto serie: {e}")
    except KeyboardInterrupt:
        print("\n[!] Interrumpido. La mesa se queda en su posición actual.")

if __name__ == "__main__":
    main()