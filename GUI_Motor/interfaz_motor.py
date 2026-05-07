import tkinter as tk
from tkinter import ttk, scrolledtext
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

# =============================================================================
# SECCIÓN: REDIRECCIÓN DE CONSOLA
# =============================================================================
class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.after(0, self._write, message)

    def _write(self, message):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END) 
        self.text_widget.configure(state='disabled')

    def flush(self):
        pass

# =============================================================================
# SECCIÓN: CLASE PRINCIPAL Y CONFIGURACIÓN INICIAL
# =============================================================================
class MotorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de Control - Mesa Rotatoria STM32")
        self.root.geometry("1020x720")
        
        # Definición de ruta para recursos
        self.ruta_base = os.path.dirname(os.path.abspath(__file__))

        # Variables de control de estado
        self.entrenando = False
        self.hilo_entrenamiento = None
        self.conexion = None
        self.log_file = None
        self.archivo_config = os.path.join(self.ruta_base, "config.json")    
        self.ruta_logo = os.path.join(self.ruta_base, "us.png") 

        # Variables de estadísticas
        self.movimientos_count = 0

        self.crear_interfaz()
        self.cargar_configuracion()
        
        sys.stdout = ConsoleRedirector(self.consola)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    # =============================================================================
    # SECCIÓN: CREACIÓN DE LA INTERFAZ (LAYOUT)
    # =============================================================================
    def crear_interfaz(self):
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

        # Configuración del Sistema
        frame_config = ttk.LabelFrame(frame_top, text="Configuración del Sistema", padding=10)
        frame_config.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ttk.Label(frame_config, text="Puerto:").grid(row=0, column=0, sticky="w")
        self.combo_puertos = ttk.Combobox(frame_config, values=self.obtener_puertos(), width=12)
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

        # Panel de Estadísticas (Reloj y Contador)
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

        # Movimiento
        frame_motor = ttk.LabelFrame(frame_motor_master, text="Parámetros de Movimiento", padding=10)
        frame_motor.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.var_rand_ang = tk.BooleanVar(value=True)
        self.var_rand_vel = tk.BooleanVar(value=True)
        self.var_rand_acc = tk.BooleanVar(value=True)
        self.var_rand_dec = tk.BooleanVar(value=True)
        self.var_link_acc_dec = tk.BooleanVar(value=True)
        
        # Checkbuttons y Entries de movimiento
        ttk.Checkbutton(frame_motor, text="Ángulo Aleatorio (-180 a 180)", variable=self.var_rand_ang, command=self.toggle_entries).grid(row=0, column=0, sticky="w")
        self.entry_ang = ttk.Entry(frame_motor, width=10)
        self.entry_ang.grid(row=0, column=2, pady=2)

        ttk.Checkbutton(frame_motor, text="Velocidad Aleatoria (200 a 800)", variable=self.var_rand_vel, command=self.toggle_entries).grid(row=1, column=0, sticky="w")
        self.entry_vel = ttk.Entry(frame_motor, width=10)
        self.entry_vel.grid(row=1, column=2, pady=2)

        ttk.Checkbutton(frame_motor, text="Aceleración Aleatoria (800 a 4000)", variable=self.var_rand_acc, command=self.toggle_entries).grid(row=2, column=0, sticky="w")
        self.entry_acc = ttk.Entry(frame_motor, width=10)
        self.entry_acc.grid(row=2, column=2, pady=2)

        self.check_rand_dec = ttk.Checkbutton(frame_motor, text="Desaceleración Aleatoria (800 a 4000)", variable=self.var_rand_dec, command=self.toggle_entries)
        self.check_rand_dec.grid(row=3, column=0, sticky="w")
        self.entry_dec = ttk.Entry(frame_motor, width=10)
        self.entry_dec.grid(row=3, column=2, pady=2)

        ttk.Checkbutton(frame_motor, text="🔗 Vincular Acc/Dec (Simétrico)", variable=self.var_link_acc_dec, command=self.toggle_entries).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8,0))

        # K-Values (Potencia)
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

        # =============================================================================
        # SECCIÓN: LÓGICA DE ICONOS Y BOTONES DE CONTROL
        # =============================================================================
        frame_botones = tk.Frame(frame_operacion)
        frame_botones.pack(side=tk.RIGHT)

        self.iconos = {}

        def preparar_icono(ruta_archivo, color_hex=None):
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

        col_blue, col_green, col_orange, col_red = "#005b96", "#008000", "#FF8C00", "#CC0000"

        self.iconos['home'] = preparar_icono("botonHome.png", col_blue)
        self.iconos['play'] = preparar_icono("botonPlay.png", col_green)
        self.iconos['stop'] = preparar_icono("botonStop.png", col_orange)
        self.iconos['quit'] = preparar_icono("botonQuit.png", col_red)

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
    # SECCIÓN: FUNCIONES DE ACTUALIZACIÓN DE UI
    # =============================================================================
    def actualizar_progreso_ui(self, movs, seg_restantes):
        def _update():
            self.label_movimientos.config(text=f"Movs: {movs}")
            if seg_restantes > 0:
                h, m, s = int(seg_restantes // 3600), int((seg_restantes % 3600) // 60), int(seg_restantes % 60)
                self.label_reloj.config(text=f"⌛ {h:02d}:{m:02d}:{s:02d}")
            else:
                self.label_reloj.config(text="⌛ 00:00:00", foreground="red")
        self.root.after(0, _update)

    def actualizar_led_conexion(self, conectado):
        def _update():
            if conectado: self.led_conexion.config(text="🟢 CONECTADO", foreground="green")
            else: self.led_conexion.config(text="🔴 DESCONECTADO", foreground="red")
        self.root.after(0, _update)

    def actualizar_led_motor(self, estado):
        def _update():
            if estado == "REPOSO": self.led_motor.config(text="⚪ MOTOR: REPOSO", foreground="gray")
            elif estado == "HOMING": self.led_motor.config(text="🟠 MOTOR: HOMING", foreground="orange")
            elif estado == "MOVIENDO": self.led_motor.config(text="🔵 MOTOR: MOVIENDO", foreground="#007acc")
        self.root.after(0, _update)

    def toggle_entries(self):
        self.entry_ang.state(['disabled'] if self.var_rand_ang.get() else ['!disabled'])
        self.entry_vel.state(['disabled'] if self.var_rand_vel.get() else ['!disabled'])
        self.entry_acc.state(['disabled'] if self.var_rand_acc.get() else ['!disabled'])
        if self.var_link_acc_dec.get():
            self.check_rand_dec.state(['disabled']); self.entry_dec.state(['disabled'])
        else:
            self.check_rand_dec.state(['!disabled'])
            self.entry_dec.state(['disabled'] if self.var_rand_dec.get() else ['!disabled'])

    # =============================================================================
    # SECCIÓN: FUNCIONES SERIAL Y COMANDOS MOTOR
    # =============================================================================
    def obtener_puertos(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def conectar_serial(self, timeout=1.0):
        if self.conexion and self.conexion.is_open: return True
        try:
            self.conexion = serial.Serial(self.combo_puertos.get(), int(self.entry_baud.get()), timeout=timeout)
            time.sleep(2)
            self.actualizar_led_conexion(True)
            return True
        except Exception as e:
            print(f"[!] Error Serial: {e}")
            return False

    def comando_enviar_kvals(self):
        if self.entrenando or not self.conectar_serial(): return
        try:
            kh, kr, ka, kd = int(self.entry_khold.get()), int(self.entry_krun.get()), int(self.entry_kacc.get()), int(self.entry_kdec.get())
            cmd = f"K:{kh},{kr},{ka},{kd}\n"
            self.conexion.write(cmd.encode())
            res = self.conexion.readline().decode('utf-8').strip()
            print(f"[✔] [STM32]: {res}")
        except Exception as e: print(f"[!] Error KVALs: {e}")

    def comando_homing(self):
        if self.entrenando or not self.conectar_serial(timeout=12.0): return
        self.actualizar_led_motor("HOMING")
        self.conexion.write(b"HOME\n")
        res = self.conexion.readline().decode('utf-8').strip()
        self.actualizar_led_motor("REPOSO")
        print(f"[✔] [STM32]: {res}")

    def comando_start(self):
        if self.entrenando or not self.conectar_serial(): return
        if not self.log_file: self.inicializar_log()
        self.entrenando = True
        self.movimientos_count = 0
        self.actualizar_led_motor("MOVIENDO")
        self.hilo_entrenamiento = threading.Thread(target=self.rutina_entrenamiento, daemon=True)
        self.hilo_entrenamiento.start()

    def comando_soft_stop(self):
        if self.entrenando:
            self.entrenando = False
            print("[...] S. STOP: Pidiendo parada segura...")

    # =============================================================================
    # SECCIÓN: LÓGICA DE ENTRENAMIENTO (HILO SECUNDARIO)
    # =============================================================================
    def rutina_entrenamiento(self):
        print("\n[▶] Ciclo de entrenamiento iniciado.")
        try:
            limite = time.time() + (float(self.entry_horas.get()) * 3600)
            espera = float(self.entry_espera.get())
            while self.entrenando and time.time() < limite:
                g = random.uniform(-180, 180) if self.var_rand_ang.get() else float(self.entry_ang.get())
                v = random.uniform(200, 800) if self.var_rand_vel.get() else float(self.entry_vel.get())
                a = random.uniform(800, 4000) if self.var_rand_acc.get() else float(self.entry_acc.get())
                d = a if self.var_link_acc_dec.get() else (random.uniform(800, 4000) if self.var_rand_dec.get() else float(self.entry_dec.get()))
                
                self.enviar_comando_dinamico(v, a, d, g)
                self.movimientos_count += 1
                self.actualizar_progreso_ui(self.movimientos_count, limite - time.time())
                
                for _ in range(int(espera * 10)):
                    if not self.entrenando: break
                    time.sleep(0.1)
                    self.actualizar_progreso_ui(self.movimientos_count, limite - time.time())
        except Exception as e: print(f"[!] Error en rutina: {e}")
        finally:
            self.entrenando = False
            self.actualizar_led_motor("REPOSO")
            print("[✔] Entrenamiento detenido.")

    def enviar_comando_dinamico(self, v, a, d, g):
        cmd = f"V:{v:.1f},A:{a:.1f},D:{d:.1f},G:{g:.2f}\n"
        self.conexion.write(cmd.encode('utf-8'))
        res = self.conexion.readline().decode('utf-8').strip() or "TIMEOUT"
        print(f"-> Ang:{g:>6.1f}º | V:{v:>4.0f} | A:{a:>4.0f} | [STM32]: {res}")

    # =============================================================================
    # SECCIÓN: GESTIÓN DE CONFIGURACIÓN Y CIERRE
    # =============================================================================
    def inicializar_log(self):
        if not os.path.exists("logs"): os.makedirs("logs")
        self.log_file = open(os.path.join("logs", f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"), "a")

    def guardar_configuracion(self):
        config = {"puerto": self.combo_puertos.get(), "baud": self.entry_baud.get(), "horas": self.entry_horas.get(), "espera": self.entry_espera.get()}
        with open(self.archivo_config, 'w') as f: json.dump(config, f)

    def cargar_configuracion(self):
        if os.path.exists(self.archivo_config):
            with open(self.archivo_config, 'r') as f:
                c = json.load(f)
                self.combo_puertos.set(c.get("puerto", ""))
                self.entry_baud.insert(0, c.get("baud", "115200"))
                self.entry_horas.insert(0, c.get("horas", "0.5"))
                self.entry_espera.insert(0, c.get("espera", "5.0"))
        self.toggle_entries()

    def cerrar_aplicacion(self):
        self.guardar_configuracion()
        self.entrenando = False
        if self.conexion: self.conexion.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorGUI(root)
    root.mainloop()