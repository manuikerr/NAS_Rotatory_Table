import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import serial
import serial.tools.list_ports
import time
import random
import os
import json
from datetime import datetime
import threading
import sys
from PIL import Image, ImageTk 
import csv

# =============================================================================
# UTILIDADES GLOBALES
# =============================================================================
def obtener_timestamp():
    """Genera una marca de tiempo con resolución de centésimas de segundo."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

# =============================================================================
# REDIRECCIÓN DE CONSOLA
# =============================================================================
class ConsoleRedirector:
    """Intercepta los prints para enviarlos a la GUI y al archivo de log."""
    def __init__(self, text_widget, func_escribir_log):
        """Inicializa el redireccionador vinculando el widget y la función de log."""
        self.text_widget = text_widget
        self.func_escribir_log = func_escribir_log

    def write(self, message):
        """Envía el mensaje a la interfaz gráfica y al archivo físico."""
        self.text_widget.after(0, self._write, message)
        self.func_escribir_log(message)

    def _write(self, message):
        """Inserta el texto en el widget de Tkinter de forma segura."""
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END) 
        self.text_widget.configure(state='disabled')

    def flush(self):
        """Método requerido por sys.stdout, no realiza ninguna acción."""
        pass

# =============================================================================
# CAPA DE LÓGICA Y HARDWARE
# =============================================================================
class MotorControl:
    """Gestiona la comunicación Serial, el hilo de entrenamiento y el archivo log."""
    
    SIMULADOR_ID = "MODO_TEST"
    MSG_ANGULO_OK = "Angulo recibido"
    MSG_TIMEOUT = "TIMEOUT"

    def __init__(self, cb_conn, cb_motor, cb_progreso):
        """Inicializa las variables y callbacks de conexión y estado."""
        self.cb_conn = cb_conn          
        self.cb_motor = cb_motor        
        self.cb_progreso = cb_progreso  
        
        self.conexion = None
        self.log_file = None
        self.entrenando = False
        self.hilo_entrenamiento = None
        
        self.rutina_csv = []
        self.movimientos_count = 0

    def inicializar_log(self):
        """Crea la carpeta de logs y abre un archivo txt con formato UTF-8."""
        ruta_script = os.path.dirname(os.path.abspath(__file__))
        carpeta_logs = os.path.join(ruta_script, "logs")
        if not os.path.exists(carpeta_logs):
            os.makedirs(carpeta_logs)
            
        nombre_archivo = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ruta_completa_log = os.path.join(carpeta_logs, nombre_archivo)
        
        print(f"[DEBUG] Guardando log en: {ruta_completa_log}")
        self.log_file = open(ruta_completa_log, "a", encoding="utf-8")

    def escribir_log(self, mensaje):
        """Guarda físicamente un mensaje en el archivo de log."""
        if getattr(self, 'log_file', None) and not getattr(self.log_file, 'closed', True):
            try:
                self.log_file.write(mensaje)
                self.log_file.flush()
            except Exception:
                pass

    def obtener_puertos(self):
        """Devuelve una lista con los puertos COM disponibles en el sistema."""
        return [p.device for p in serial.tools.list_ports.comports()]

    def conectar_serial(self, puerto, baud, es_simulador, timeout=1.0):
        """Abre la conexión serie con el hardware o activa el simulador."""
        if not self.log_file: 
            self.inicializar_log()

        if es_simulador:
            self.conexion = self.SIMULADOR_ID
            self.cb_conn(True)
            return True

        if getattr(self.conexion, 'is_open', False): 
            return True
        
        try:
            self.conexion = serial.Serial(puerto, int(baud), timeout=timeout)
            time.sleep(2)
            self.cb_conn(True)
            return True
        except Exception as e:
            print(f"[!] Error Serial: {e}")
            return False

    def enviar_kvals(self, kh, kr, ka, kd):
        """Envía los parámetros de potencia (Hold, Run, Acc, Dec) al driver."""
        cmd = f"K:{kh},{kr},{ka},{kd}\n"
        print(f"[PC] Enviando configuración KVALs: {cmd.strip()}")            
        
        if self.conexion == self.SIMULADOR_ID:
            res = f"KVAL OK -> HOLD:{kh}% RUN:{kr}% ACC:{ka}% DEC:{kd}%"
        else:
            self.conexion.write(cmd.encode())
            res = self.conexion.readline().decode('utf-8').strip()
            
        print(f"[✔] [STM32]: {res}")

    def ejecutar_homing(self):
        """Lanza el comando HOME para buscar el punto cero de la máquina."""
        print(f"[{obtener_timestamp()}] [PC] Ejecutando rutina de Homing...")
        self.cb_motor("HOMING")
        
        if self.conexion == self.SIMULADOR_ID:
            time.sleep(1)
            res = "Homing completado"
        else:
            self.conexion.write(b"HOME\n")
            res = self.conexion.readline().decode('utf-8').strip()
            
        self.cb_motor("REPOSO")
        print(f"[{obtener_timestamp()}] [✔] [STM32]: {res}")

    def iniciar_entrenamiento(self, horas, espera, cfg):
        """Arranca el hilo secundario para ejecutar la rutina de movimientos."""
        self.entrenando = True
        self.movimientos_count = 0
        self.cb_motor("MOVIENDO")
        self.hilo_entrenamiento = threading.Thread(
            target=self._rutina_entrenamiento, 
            args=(horas, espera, cfg), 
            daemon=True
        )
        self.hilo_entrenamiento.start()

    def _rutina_entrenamiento(self, horas, espera, cfg):
        """Bucle principal que calcula y envía los ángulos continuamente."""
        print(f"\n[▶] Ciclo de entrenamiento iniciado (Duración: {horas}h | Pausa: {espera}s)")
        try:
            limite = time.time() + (horas * 3600)
            while self.entrenando and time.time() < limite:
                
                if self.rutina_csv:
                    if not cfg['ciclico_csv'] and self.movimientos_count >= len(self.rutina_csv):
                        print("[INFO] Rutina CSV finalizada (Modo no cíclico).")
                        break

                    indice = self.movimientos_count % len(self.rutina_csv)
                    v, a, d, g = self.rutina_csv[indice]
                else:
                    g = random.uniform(-180, 180) if cfg['rand_ang'] else cfg['val_ang']
                    v = random.uniform(200, 800) if cfg['rand_vel'] else cfg['val_vel']
                    a = random.uniform(800, 4000) if cfg['rand_acc'] else cfg['val_acc']
                    d = a if cfg['link_acc_dec'] else (random.uniform(800, 4000) if cfg['rand_dec'] else cfg['val_dec'])
                
                self._enviar_comando_dinamico(v, a, d, g)
                self.movimientos_count += 1
                self.cb_progreso(self.movimientos_count, limite - time.time())
                
                for _ in range(int(espera * 10)):
                    if not self.entrenando: break
                    time.sleep(0.1)
                    self.cb_progreso(self.movimientos_count, limite - time.time())
        except Exception as e: 
            print(f"[!] Error en rutina: {e}")
        finally:
            self.entrenando = False
            self.cb_motor("REPOSO")
            print("[✔] Entrenamiento detenido.")

    def _enviar_comando_dinamico(self, v, a, d, g):
        """Formatea y envía la trama de Velocidad, Aceleración, Desaceleración y Grados."""
        cmd = f"V:{v:.1f},A:{a:.1f},D:{d:.1f},G:{g:.2f}\n"
        
        if self.conexion == self.SIMULADOR_ID:
            time.sleep(0.05)
            res = self.MSG_ANGULO_OK
        else:
            self.conexion.write(cmd.encode('utf-8'))
            res = self.conexion.readline().decode('utf-8').strip() or self.MSG_TIMEOUT
            
        print(f"[{obtener_timestamp()}] [PC] Ang:{g:>6.1f}º | V:{v:>4.0f} | A:{a:>4.0f} | D:{d:>4.0f} | -> [STM32]: {res}")

    def detener_entrenamiento(self):
        """Señaliza la detención de la rutina de entrenamiento de forma segura."""
        if self.entrenando:
            self.entrenando = False
            print(f"[{obtener_timestamp()}] [PC] SOFT STOP: Pidiendo parada segura...")

    def cerrar_conexion(self):
        """Cierra el puerto COM y el archivo de log correctamente."""
        self.entrenando = False
        if self.conexion and self.conexion != self.SIMULADOR_ID:
            try: self.conexion.close()
            except Exception: pass
                
        if getattr(self, 'log_file', None) and not getattr(self.log_file, 'closed', True):
            try: self.log_file.close()
            except Exception: pass

# =============================================================================
# CAPA DE INTERFAZ GRÁFICA
# =============================================================================
class MotorGUI:
    """Gestiona exclusivamente el renderizado y los eventos de la ventana de Tkinter."""
    
    def __init__(self, root):
        """Inicializa la ventana principal, rutas base y la capa de lógica."""
        self.root = root
        self.root.title("Panel de Control - Mesa Rotatoria STM32")
        self.root.geometry("1020x720")
        
        self.ruta_base = os.path.dirname(os.path.abspath(__file__))
        self.archivo_config = os.path.join(self.ruta_base, "config.json")    
        self.ruta_logo = os.path.join(self.ruta_base, "us.png") 

        self.motor = MotorControl(
            cb_conn=self.actualizar_led_conexion,
            cb_motor=self.actualizar_led_motor,
            cb_progreso=self.actualizar_progreso_ui
        )

        self.crear_interfaz()
        self.cargar_configuracion()
        
        sys.stdout = ConsoleRedirector(self.consola, self.motor.escribir_log)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    def _preparar_icono(self, ruta_archivo, color_hex=None):
        """Carga, redimensiona y aplica tinte a las imágenes de los botones."""
        try:
            full_path = os.path.join(self.ruta_base, ruta_archivo)
            img = Image.open(full_path).convert("RGBA")
            img = img.resize((18, 18), Image.Resampling.LANCZOS)
            if color_hex:
                color_hex = color_hex.lstrip('#')
                rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                r, g, b, a = img.split()
                img = Image.merge("RGBA", (r.point(lambda _: rgb[0]), r.point(lambda _: rgb[1]), r.point(lambda _: rgb[2]), a))
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def crear_interfaz(self):
        """Construye todos los elementos visuales de la ventana (Labels, Frames, Botones)."""
        # --- ENCABEZADO ---
        frame_encabezado = tk.Frame(self.root)
        frame_encabezado.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        self.root.grid_columnconfigure(0, weight=1)

        try:
            img = Image.open(self.ruta_logo)
            nuevo_alto = 50
            nuevo_ancho = int((img.size[0] * nuevo_alto) / img.size[1])
            img = img.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            tk.Label(frame_encabezado, image=self.photo).pack(side=tk.LEFT, padx=10)
        except Exception:
            tk.Label(frame_encabezado, text="[LOGO]", font=("Arial", 12), bg="#ddd", width=8, height=2).pack(side=tk.LEFT, padx=10)

        txt_creditos = "Desarrollado por:\nÁngel Francisco Jiménez Fernández & Manuel Martín Aguaded"
        tk.Label(frame_encabezado, text=txt_creditos, justify=tk.RIGHT, font=("Arial", 9, "italic"), fg="#555").pack(side=tk.RIGHT, padx=10)

        # --- PANEL SUPERIOR: CONFIGURACIÓN Y ESTADÍSTICAS ---
        frame_top = tk.Frame(self.root)
        frame_top.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        frame_top.columnconfigure(0, weight=4)
        frame_top.columnconfigure(1, weight=1)

        frame_config = ttk.LabelFrame(frame_top, text="Configuración del Sistema", padding=10)
        frame_config.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ttk.Label(frame_config, text="Puerto:").grid(row=0, column=0, sticky="w")
        self.combo_puertos = ttk.Combobox(frame_config, values=self.motor.obtener_puertos(), width=12)
        self.combo_puertos.grid(row=0, column=1, padx=5)
        
        ttk.Label(frame_config, text="Baud:").grid(row=0, column=2, padx=(10, 0))
        self.entry_baud = ttk.Entry(frame_config, width=8)
        self.entry_baud.grid(row=0, column=3, padx=5)

        ttk.Label(frame_config, text="Horas:").grid(row=0, column=4, padx=(10, 0))
        self.entry_horas = ttk.Entry(frame_config, width=6)
        self.entry_horas.grid(row=0, column=5, padx=5)

        ttk.Label(frame_config, text="Pausa(s):").grid(row=0, column=6, padx=(10, 0))
        self.entry_espera = ttk.Entry(frame_config, width=6)
        self.entry_espera.grid(row=0, column=7, padx=5)

        self.var_simulador = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_config, text="Simulador", variable=self.var_simulador, command=self.toggle_simulador).grid(row=0, column=8, padx=(10,0))

        frame_progreso = ttk.LabelFrame(frame_top, text="Estadísticas", padding=10)
        frame_progreso.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.label_movimientos = ttk.Label(frame_progreso, text="Movs: 0", font=("Arial", 10, "bold"))
        self.label_movimientos.grid(row=0, column=0, padx=10)

        self.label_reloj = ttk.Label(frame_progreso, text="⌛ 00:00:00", font=("Consolas", 11, "bold"), foreground="#005b96")
        self.label_reloj.grid(row=0, column=1, padx=10)

        # --- PANEL CENTRAL: PARÁMETROS MOTOR ---
        frame_motor_master = tk.Frame(self.root)
        frame_motor_master.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        frame_motor_master.columnconfigure(0, weight=3)
        frame_motor_master.columnconfigure(1, weight=1)

        frame_motor = ttk.LabelFrame(frame_motor_master, text="Parámetros de Movimiento", padding=10)
        frame_motor.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.var_rand_ang = tk.BooleanVar(value=True)
        self.var_rand_vel = tk.BooleanVar(value=True)
        self.var_rand_acc = tk.BooleanVar(value=True)
        self.var_rand_dec = tk.BooleanVar(value=True)
        self.var_link_acc_dec = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(frame_motor, text="Ángulo Aleatorio (-180 a 180)", variable=self.var_rand_ang, command=self.toggle_entries).grid(row=0, column=0, sticky="w")
        ttk.Label(frame_motor, text="Fijo:").grid(row=0, column=1, padx=5)
        self.entry_ang = ttk.Entry(frame_motor, width=10)
        self.entry_ang.grid(row=0, column=2, pady=2)

        ttk.Checkbutton(frame_motor, text="Velocidad Aleatoria (200 a 800)", variable=self.var_rand_vel, command=self.toggle_entries).grid(row=1, column=0, sticky="w")
        ttk.Label(frame_motor, text="Fijo:").grid(row=1, column=1, padx=5)
        self.entry_vel = ttk.Entry(frame_motor, width=10)
        self.entry_vel.grid(row=1, column=2, pady=2)

        ttk.Checkbutton(frame_motor, text="Aceleración Aleatoria (800 a 4000)", variable=self.var_rand_acc, command=self.toggle_entries).grid(row=2, column=0, sticky="w")
        ttk.Label(frame_motor, text="Fijo:").grid(row=2, column=1, padx=5)
        self.entry_acc = ttk.Entry(frame_motor, width=10)
        self.entry_acc.grid(row=2, column=2, pady=2)

        self.check_rand_dec = ttk.Checkbutton(frame_motor, text="Desaceleración Aleatoria (800 a 4000)", variable=self.var_rand_dec, command=self.toggle_entries)
        self.check_rand_dec.grid(row=3, column=0, sticky="w")
        ttk.Label(frame_motor, text="Fijo:").grid(row=3, column=1, padx=5)
        self.entry_dec = ttk.Entry(frame_motor, width=10)
        self.entry_dec.grid(row=3, column=2, pady=2)

        ttk.Checkbutton(frame_motor, text="🔗 Vincular Acc/Dec (Simétrico)", variable=self.var_link_acc_dec, command=self.toggle_entries).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8,0))

        # --- SECCIÓN CSV ---
        ttk.Separator(frame_motor, orient="horizontal").grid(row=5, column=0, columnspan=3, sticky="ew", pady=(15, 10))

        frame_csv = tk.Frame(frame_motor)
        frame_csv.grid(row=6, column=0, columnspan=3, sticky="w")

        self.var_ciclico_csv = tk.BooleanVar(value=True)
        self.check_ciclico = ttk.Checkbutton(frame_csv, text="Cíclico", variable=self.var_ciclico_csv)
        self.check_ciclico.pack(side=tk.LEFT, padx=10)

        ttk.Button(frame_csv, text="Cargar Rutina CSV", command=self.comando_cargar_csv).pack(side=tk.LEFT)
        
        self.btn_borrar_csv = ttk.Button(frame_csv, text="✖", width=3, command=self.borrar_rutina_csv)
        self.btn_borrar_csv.pack(side=tk.LEFT, padx=5)
        self.btn_borrar_csv.state(['disabled'])

        self.label_csv = ttk.Label(frame_csv, text="Modo: Aleatorio/Fijo", font=("Arial", 8, "italic"), foreground="gray")
        self.label_csv.pack(side=tk.LEFT, padx=5)

        # --- K-VALUES ---
        frame_kval = ttk.LabelFrame(frame_motor_master, text="K_Values (Potencia: 0% - 100%)", padding=10)
        frame_kval.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        ttk.Label(frame_kval, text="HOLD:").grid(row=0, column=0, pady=5)
        self.entry_khold = ttk.Entry(frame_kval, width=6)
        self.entry_khold.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame_kval, text="RUN:").grid(row=0, column=2, pady=5)
        self.entry_krun = ttk.Entry(frame_kval, width=6)
        self.entry_krun.grid(row=0, column=3, pady=5)

        ttk.Label(frame_kval, text="ACC:").grid(row=1, column=0, pady=5)
        self.entry_kacc = ttk.Entry(frame_kval, width=6)
        self.entry_kacc.grid(row=1, column=1, pady=5)

        ttk.Label(frame_kval, text="DEC:").grid(row=1, column=2, pady=5)
        self.entry_kdec = ttk.Entry(frame_kval, width=6)
        self.entry_kdec.grid(row=1, column=3, pady=5)

        ttk.Button(frame_kval, text="⚡ APLICAR KVALS", command=self.comando_enviar_kvals).grid(row=2, column=0, columnspan=4, pady=(15,0), sticky="ew")

        # --- PANEL INFERIOR: ESTADO Y BOTONES ---
        frame_operacion = tk.Frame(self.root)
        frame_operacion.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        frame_estado = ttk.LabelFrame(frame_operacion, text="Estado de la Máquina", padding=5)
        frame_estado.pack(side=tk.LEFT, fill=tk.Y)
        
        self.led_conexion = ttk.Label(frame_estado, text="🔴 DESCONECTADO", font=("Arial", 9, "bold"), foreground="red", width=16)
        self.led_conexion.pack(side=tk.LEFT, padx=10)
        
        self.led_motor = ttk.Label(frame_estado, text="⚪ MOTOR: REPOSO", font=("Arial", 9, "bold"), foreground="gray", width=18)
        self.led_motor.pack(side=tk.LEFT, padx=10)

        frame_botones = tk.Frame(frame_operacion)
        frame_botones.pack(side=tk.RIGHT)

        col_blue, col_green, col_orange, col_red = "#005b96", "#008000", "#FF8C00", "#CC0000"

        self.iconos = {
            'home': self._preparar_icono("botonHome.png", col_blue),
            'play': self._preparar_icono("botonPlay.png", col_green),
            'stop': self._preparar_icono("botonStop.png", col_orange),
            'quit': self._preparar_icono("botonQuit.png", col_red)
        }

        style = ttk.Style()
        style.configure("Home.TButton", font=("Arial", 9, "bold"), foreground=col_blue)
        style.configure("Start.TButton", font=("Arial", 9, "bold"), foreground=col_green)
        style.configure("Finish.TButton", font=("Arial", 9, "bold"), foreground=col_orange)
        style.configure("Quit.TButton", font=("Arial", 9, "bold"), foreground=col_red)

        ttk.Button(frame_botones, text=" HOMING", image=self.iconos['home'], style="Home.TButton", command=self.comando_homing, width=12, compound=tk.LEFT).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text=" START", image=self.iconos['play'], style="Start.TButton", command=self.comando_start, width=12, compound=tk.LEFT).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text=" S. STOP", image=self.iconos['stop'], style="Finish.TButton", command=self.comando_soft_stop, width=12, compound=tk.LEFT).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text=" QUIT", image=self.iconos['quit'], style="Quit.TButton", command=self.cerrar_aplicacion, width=12, compound=tk.LEFT).pack(side=tk.LEFT, padx=5)

        # --- CONSOLA ---
        frame_consola = ttk.LabelFrame(self.root, text="Consola de Telemetría (Real-time)", padding=10)
        frame_consola.grid(row=4, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.root.grid_rowconfigure(4, weight=1)

        self.consola = scrolledtext.ScrolledText(frame_consola, bg="#0c0c0c", fg="#33ff33", font=("Consolas", 10), state='disabled')
        self.consola.pack(fill=tk.BOTH, expand=True)

    # =============================================================================
    # DELEGACIÓN DE EVENTOS UI Y CALLBACKS
    # =============================================================================
    def toggle_simulador(self):
        """Alterna entre hardware real y modo simulador, bloqueando el puerto."""
        if self.var_simulador.get():
            self.combo_puertos.set("SIMULADOR")
            self.combo_puertos.state(['disabled'])
            print("[INFO] Modo de simulación activado.")
        else:
            self.combo_puertos.state(['!disabled'])
            self.combo_puertos.set("")
            if self.motor.conexion == MotorControl.SIMULADOR_ID:
                self.motor.conexion = None
                self.actualizar_led_conexion(False)
            print("[INFO] Modo de simulación desactivado.")

    def actualizar_progreso_ui(self, movs, seg_restantes):
        """Actualiza el texto del reloj y movimientos en la GUI (hilo seguro)."""
        def _update():
            self.label_movimientos.config(text=f"Movs: {movs}")
            if seg_restantes > 0:
                h, m, s = int(seg_restantes // 3600), int((seg_restantes % 3600) // 60), int(seg_restantes % 60)
                self.label_reloj.config(text=f"⌛ {h:02d}:{m:02d}:{s:02d}")
            else:
                self.label_reloj.config(text="⌛ 00:00:00", foreground="red")
        self.root.after(0, _update)

    def actualizar_led_conexion(self, conectado):
        """Cambia el texto y color del indicador de estado de conexión."""
        def _update():
            if conectado: self.led_conexion.config(text="🟢 CONECTADO", foreground="green")
            else: self.led_conexion.config(text="🔴 DESCONECTADO", foreground="red")
        self.root.after(0, _update)

    def actualizar_led_motor(self, estado):
        """Cambia el texto y color indicando si el motor se mueve, hace homing o reposa."""
        def _update():
            if estado == "REPOSO": self.led_motor.config(text="⚪ MOTOR: REPOSO", foreground="gray")
            elif estado == "HOMING": self.led_motor.config(text="🟠 MOTOR: HOMING", foreground="orange")
            elif estado == "MOVIENDO": self.led_motor.config(text="🔵 MOTOR: MOVIENDO", foreground="#007acc")
        self.root.after(0, _update)

    def toggle_entries(self):
        """Bloquea los campos manuales si las casillas aleatorias o un CSV están activos."""
        hay_csv = len(self.motor.rutina_csv) > 0
        
        self.entry_ang.state(['disabled'] if self.var_rand_ang.get() or hay_csv else ['!disabled'])
        self.entry_vel.state(['disabled'] if self.var_rand_vel.get() or hay_csv else ['!disabled'])
        self.entry_acc.state(['disabled'] if self.var_rand_acc.get() or hay_csv else ['!disabled'])
        
        if self.var_link_acc_dec.get() or hay_csv:
            self.check_rand_dec.state(['disabled'])
            self.entry_dec.state(['disabled'])
        else:
            self.check_rand_dec.state(['!disabled'])
            self.entry_dec.state(['disabled'] if self.var_rand_dec.get() else ['!disabled'])

    # =============================================================================
    # COMANDOS A CAPA DE LÓGICA
    # =============================================================================
    def comando_enviar_kvals(self):
        """Recoge los valores KVAL de la interfaz y los manda al controlador."""
        if self.motor.entrenando: return
        try:
            kh, kr, ka, kd = int(self.entry_khold.get()), int(self.entry_krun.get()), int(self.entry_kacc.get()), int(self.entry_kdec.get())
            puerto = self.combo_puertos.get()
            baud = self.entry_baud.get()
            simulador = self.var_simulador.get()
            
            if self.motor.conectar_serial(puerto, baud, simulador):
                self.motor.enviar_kvals(kh, kr, ka, kd)
        except ValueError:
            print("[!] Error KVALs: Valores inválidos.")

    def comando_homing(self):
        """Delega la ejecución de la rutina Homing a la clase MotorControl."""
        if self.motor.entrenando: return
        puerto = self.combo_puertos.get()
        baud = self.entry_baud.get()
        simulador = self.var_simulador.get()
        
        if self.motor.conectar_serial(puerto, baud, simulador, timeout=12.0):
            self.motor.ejecutar_homing()

    def comando_start(self):
        """Recopila toda la configuración de la GUI y ordena iniciar la rutina."""
        if self.motor.entrenando: return
        try:
            horas = float(self.entry_horas.get())
            espera = float(self.entry_espera.get())
            puerto = self.combo_puertos.get()
            baud = self.entry_baud.get()
            simulador = self.var_simulador.get()
            
            cfg = {
                'ciclico_csv': self.var_ciclico_csv.get(),
                'rand_ang': self.var_rand_ang.get(),
                'val_ang': float(self.entry_ang.get()) if not self.var_rand_ang.get() else 0.0,
                'rand_vel': self.var_rand_vel.get(),
                'val_vel': float(self.entry_vel.get()) if not self.var_rand_vel.get() else 0.0,
                'rand_acc': self.var_rand_acc.get(),
                'val_acc': float(self.entry_acc.get()) if not self.var_rand_acc.get() else 0.0,
                'link_acc_dec': self.var_link_acc_dec.get(),
                'rand_dec': self.var_rand_dec.get(),
                'val_dec': float(self.entry_dec.get()) if not self.var_rand_dec.get() else 0.0
            }
            
            if self.motor.conectar_serial(puerto, baud, simulador):
                self.motor.iniciar_entrenamiento(horas, espera, cfg)
        except ValueError:
            print("[!] Error: Revisa los valores manuales introducidos.")

    def comando_soft_stop(self):
        """Solicita la parada controlada del entrenamiento."""
        self.motor.detener_entrenamiento()
    
    def comando_cargar_csv(self):
        """Abre un diálogo, lee un archivo CSV y carga los movimientos."""
        archivo = filedialog.askopenfilename(
            title="Seleccionar rutina de entrenamiento",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not archivo: return
            
        try:
            with open(archivo, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rutina_temp = []
                for fila in reader:
                    v = float(fila.get('V', 500))
                    a = float(fila.get('A', 1000))
                    d = float(fila.get('D', 1000))
                    g = float(fila.get('G', 90))
                    rutina_temp.append((v, a, d, g))
                    
            if rutina_temp:
                self.motor.rutina_csv = rutina_temp
                nombre_archivo = os.path.basename(archivo)
                self.label_csv.config(text=f"{nombre_archivo} ({len(rutina_temp)} movs)", foreground="green")
                self.btn_borrar_csv.state(['!disabled'])
                self.toggle_entries()
                print(f"[✔] CSV cargado con éxito: {nombre_archivo}")
            else:
                print("[!] El archivo CSV está vacío o el formato es incorrecto.")
        except Exception as e:
            print(f"[!] Error al leer el CSV: {e}")
        
    def borrar_rutina_csv(self):
        """Vacía la memoria del CSV y restaura los controles manuales de la interfaz."""
        self.motor.rutina_csv = []
        self.label_csv.config(text="Modo: Aleatorio/Fijo", foreground="gray")
        self.btn_borrar_csv.state(['disabled'])
        self.toggle_entries()
        print("[-] Rutina CSV descartada. Volviendo a modo manual.")

    # =============================================================================
    # CONFIGURACIÓN LOCAL Y CIERRE
    # =============================================================================
    def guardar_configuracion(self):
        """Guarda los parámetros de conexión y tiempo en config.json al cerrar."""
        config = {
            "puerto": self.combo_puertos.get(), 
            "baud": self.entry_baud.get(), 
            "horas": self.entry_horas.get(), 
            "espera": self.entry_espera.get()
        }
        with open(self.archivo_config, 'w') as f: 
            json.dump(config, f)

    def cargar_configuracion(self):
        """Carga los parámetros desde config.json y rellena los campos al iniciar."""
        if os.path.exists(self.archivo_config):
            with open(self.archivo_config, 'r') as f:
                c = json.load(f)
                self.combo_puertos.set(c.get("puerto", ""))
                self.entry_baud.insert(0, c.get("baud", "115200"))
                self.entry_horas.insert(0, c.get("horas", "0.5"))
                self.entry_espera.insert(0, c.get("espera", "5.0"))
        self.toggle_entries()

    def cerrar_aplicacion(self):
        """Función llamada al cerrar la ventana. Guarda datos y libera recursos."""
        self.guardar_configuracion()
        self.motor.cerrar_conexion()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorGUI(root)
    root.mainloop()