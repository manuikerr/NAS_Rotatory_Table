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

# --- REDIRECCIÓN DE CONSOLA A LA UI ---
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

# --- CLASE PRINCIPAL DE LA INTERFAZ ---
class MotorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de Control - Mesa Rotatoria STM32")
        self.root.geometry("880x880")
        ruta_base = os.path.dirname(os.path.abspath(__file__))

        # Variables de control
        self.entrenando = False
        self.hilo_entrenamiento = None
        self.conexion = None
        self.log_file = None
        self.archivo_config = os.path.join(ruta_base, "config.json")    
        self.ruta_logo = os.path.join(ruta_base, "us.png") 

        self.crear_interfaz()
        self.cargar_configuracion()
        
        sys.stdout = ConsoleRedirector(self.consola)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

    def crear_interfaz(self):
        # --- FRAME ENCABEZADO (Logo y Nombres) ---
        frame_encabezado = tk.Frame(self.root)
        frame_encabezado.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        # Cargar Logo
        try:
            img = Image.open(self.ruta_logo)
            ancho, alto = img.size
            nuevo_alto = 60
            nuevo_ancho = int((ancho * nuevo_alto) / alto)
            img = img.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            tk.Label(frame_encabezado, image=self.photo).pack(side=tk.LEFT, padx=10)
        except Exception:
            tk.Label(frame_encabezado, text="[LOGO]", font=("Arial", 14), bg="#ddd", width=8, height=2).pack(side=tk.LEFT, padx=10)

        # Créditos
        persona_1 = "Ángel Francisco Jiménez Fernández"
        persona_2 = "Manuel Martín Aguaded" 
        txt_creditos = f"Desarrollado por:\n{persona_1} & {persona_2}"
        tk.Label(frame_encabezado, text=txt_creditos, justify=tk.RIGHT, font=("Arial", 9, "italic"), fg="#555").pack(side=tk.RIGHT, padx=10)

        # --- FRAME CONFIGURACIÓN GENERAL ---
        frame_config = ttk.LabelFrame(self.root, text="Configuración del Sistema", padding=10)
        frame_config.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(frame_config, text="Puerto COM:").grid(row=0, column=0, sticky="w")
        self.combo_puertos = ttk.Combobox(frame_config, values=self.obtener_puertos(), width=15)
        self.combo_puertos.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_config, text="↻ Refrescar", command=self.refrescar_puertos).grid(row=0, column=2, padx=5)

        ttk.Label(frame_config, text="Baud Rate:").grid(row=0, column=3, sticky="w", padx=(20, 0))
        self.entry_baud = ttk.Entry(frame_config, width=10)
        self.entry_baud.grid(row=0, column=4, padx=5, pady=5)

        ttk.Label(frame_config, text="Duración (Horas):").grid(row=1, column=0, sticky="w")
        self.entry_horas = ttk.Entry(frame_config, width=10)
        self.entry_horas.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(frame_config, text="Pausa entre envíos (s):").grid(row=1, column=3, sticky="w", padx=(20, 0))
        self.entry_espera = ttk.Entry(frame_config, width=10)
        self.entry_espera.grid(row=1, column=4, padx=5, pady=5, sticky="w")

        # --- FRAME PARÁMETROS DEL MOTOR ---
        frame_motor = ttk.LabelFrame(self.root, text="Parámetros de Movimiento", padding=10)
        frame_motor.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.var_rand_ang = tk.BooleanVar(value=True)
        self.var_rand_vel = tk.BooleanVar(value=True)
        self.var_rand_acc = tk.BooleanVar(value=True)
        self.var_rand_dec = tk.BooleanVar(value=True)
        self.var_link_acc_dec = tk.BooleanVar(value=True)

        # Filas de parámetros
        params = [
            ("Ángulo Aleatorio (-180 a 180)", self.var_rand_ang, "entry_ang"),
            ("Velocidad Aleatoria (200 a 800)", self.var_rand_vel, "entry_vel"),
            ("Aceleración Aleatoria (800 a 4000)", self.var_rand_acc, "entry_acc")
        ]

        for i, (txt, var, ent_name) in enumerate(params):
            ttk.Checkbutton(frame_motor, text=txt, variable=var, command=self.toggle_entries).grid(row=i, column=0, sticky="w")
            ttk.Label(frame_motor, text="Fijo:").grid(row=i, column=1, padx=5)
            setattr(self, ent_name, ttk.Entry(frame_motor, width=10))
            getattr(self, ent_name).grid(row=i, column=2, pady=2)

        # Desaceleración (Especial para el sombreado)
        self.check_rand_dec = ttk.Checkbutton(frame_motor, text="Desaceleración Aleatoria (800 a 4000)", 
                                              variable=self.var_rand_dec, command=self.toggle_entries)
        self.check_rand_dec.grid(row=3, column=0, sticky="w")
        ttk.Label(frame_motor, text="Fijo:").grid(row=3, column=1, padx=5)
        self.entry_dec = ttk.Entry(frame_motor, width=10)
        self.entry_dec.grid(row=3, column=2, pady=2)

        # Checkbox de Vinculación
        ttk.Checkbutton(frame_motor, text="🔗 Vincular Acc/Dec (Mismo valor simétrico, Dec toma el valor que genere Acc)", 
                        variable=self.var_link_acc_dec, command=self.toggle_entries).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8,0))

        # --- FRAME KVAL (NUEVO - PORCENTAJES) ---
        frame_kval = ttk.LabelFrame(self.root, text="K_Values (Potencia Motor: 0% - 100%)", padding=10)
        frame_kval.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        ttk.Label(frame_kval, text="HOLD:").grid(row=0, column=0, padx=(0,5))
        self.entry_khold = ttk.Entry(frame_kval, width=5)
        self.entry_khold.grid(row=0, column=1, padx=(0,15))
        
        ttk.Label(frame_kval, text="RUN:").grid(row=0, column=2, padx=(0,5))
        self.entry_krun = ttk.Entry(frame_kval, width=5)
        self.entry_krun.grid(row=0, column=3, padx=(0,15))

        ttk.Label(frame_kval, text="ACC:").grid(row=0, column=4, padx=(0,5))
        self.entry_kacc = ttk.Entry(frame_kval, width=5)
        self.entry_kacc.grid(row=0, column=5, padx=(0,15))

        ttk.Label(frame_kval, text="DEC:").grid(row=0, column=6, padx=(0,5))
        self.entry_kdec = ttk.Entry(frame_kval, width=5)
        self.entry_kdec.grid(row=0, column=7, padx=(0,15))

        ttk.Button(frame_kval, text="⚡ APLICAR KVALS", command=self.comando_enviar_kvals).grid(row=0, column=8, padx=20)


        # --- FRAME BOTONES DE CONTROL ---
        frame_botones = tk.Frame(self.root)
        frame_botones.grid(row=4, column=0, padx=10, pady=15)

        style = ttk.Style()
        style.configure("H.TButton", font=("Arial", 10, "bold"), foreground="blue")
        style.configure("S.TButton", font=("Arial", 10, "bold"), foreground="green")
        style.configure("F.TButton", font=("Arial", 10, "bold"), foreground="orange")
        style.configure("Q.TButton", font=("Arial", 10, "bold"), foreground="#cc0000")

        ttk.Button(frame_botones, text="⌂ HOMING", style="H.TButton", command=self.comando_homing, width=15).grid(row=0, column=0, padx=10)
        ttk.Button(frame_botones, text="▶ START", style="S.TButton", command=self.comando_start, width=15).grid(row=0, column=1, padx=10)
        ttk.Button(frame_botones, text="■ FINISH", style="F.TButton", command=self.comando_finish, width=15).grid(row=0, column=2, padx=10)
        ttk.Button(frame_botones, text="✖ QUIT", style="Q.TButton", command=self.cerrar_aplicacion, width=15).grid(row=0, column=3, padx=10)

        # --- FRAME CONSOLA ---
        frame_consola = ttk.LabelFrame(self.root, text="Consola de Telemetría (Real-time)", padding=10)
        frame_consola.grid(row=5, column=0, padx=10, pady=10, sticky="nsew")
        self.root.grid_rowconfigure(5, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.consola = scrolledtext.ScrolledText(frame_consola, bg="#0c0c0c", fg="#33ff33", font=("Consolas", 10), state='disabled')
        self.consola.pack(fill=tk.BOTH, expand=True)

    def obtener_puertos(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def refrescar_puertos(self):
        self.combo_puertos['values'] = self.obtener_puertos()
        if self.combo_puertos['values']: self.combo_puertos.current(0)

    def toggle_entries(self):
        # Entradas estándar
        self.entry_ang.state(['disabled'] if self.var_rand_ang.get() else ['!disabled'])
        self.entry_vel.state(['disabled'] if self.var_rand_vel.get() else ['!disabled'])
        self.entry_acc.state(['disabled'] if self.var_rand_acc.get() else ['!disabled'])
        
        # Sombreado inteligente de Desaceleración
        if self.var_link_acc_dec.get():
            self.check_rand_dec.state(['disabled'])
            self.entry_dec.state(['disabled'])
        else:
            self.check_rand_dec.state(['!disabled'])
            self.entry_dec.state(['disabled'] if self.var_rand_dec.get() else ['!disabled'])

    def guardar_configuracion(self):
        config = {
            "puerto": self.combo_puertos.get(), "baud": self.entry_baud.get(),
            "horas": self.entry_horas.get(), "espera": self.entry_espera.get(),
            "r_ang": self.var_rand_ang.get(), "r_vel": self.var_rand_vel.get(),
            "r_acc": self.var_rand_acc.get(), "r_dec": self.var_rand_dec.get(),
            "link": self.var_link_acc_dec.get(),
            "f_ang": self.entry_ang.get(), "f_vel": self.entry_vel.get(),
            "f_acc": self.entry_acc.get(), "f_dec": self.entry_dec.get(),
            "k_hold": self.entry_khold.get(), "k_run": self.entry_krun.get(),
            "k_acc": self.entry_kacc.get(), "k_dec": self.entry_kdec.get()
        }
        with open(self.archivo_config, 'w') as f: json.dump(config, f)

    def cargar_configuracion(self):
        if os.path.exists(self.archivo_config):
            with open(self.archivo_config, 'r') as f:
                c = json.load(f)
                self.combo_puertos.set(c.get("puerto", ""))
                self.entry_baud.insert(0, c.get("baud", "115200"))
                self.entry_horas.insert(0, c.get("horas", "0.5"))
                self.entry_espera.insert(0, c.get("espera", "5.0"))
                self.var_rand_ang.set(c.get("r_ang", True))
                self.var_rand_vel.set(c.get("r_vel", True))
                self.var_rand_acc.set(c.get("r_acc", True))
                self.var_rand_dec.set(c.get("r_dec", True))
                self.var_link_acc_dec.set(c.get("link", True))
                self.entry_ang.insert(0, c.get("f_ang", "90.0"))
                self.entry_vel.insert(0, c.get("f_vel", "500.0"))
                self.entry_acc.insert(0, c.get("f_acc", "1000.0"))
                self.entry_dec.insert(0, c.get("f_dec", "1000.0"))
                # Valores por defecto en porcentaje
                self.entry_khold.insert(0, c.get("k_hold", "10"))
                self.entry_krun.insert(0, c.get("k_run", "30"))
                self.entry_kacc.insert(0, c.get("k_acc", "30"))
                self.entry_kdec.insert(0, c.get("k_dec", "30"))
        else:
            for e, v in [(self.entry_baud, "115200"), (self.entry_horas, "0.5"), (self.entry_espera, "5.0")]:
                e.insert(0, v)
            self.refrescar_puertos()
        self.toggle_entries()

    def conectar_serial(self, timeout=1.0):
        if self.conexion and self.conexion.is_open:
            self.conexion.timeout = timeout
            return True
        try:
            self.conexion = serial.Serial(self.combo_puertos.get(), int(self.entry_baud.get()), timeout=timeout)
            time.sleep(2)
            return True
        except Exception as e:
            print(f"[!] Error Serial: {e}")
            return False

    def inicializar_log(self):
        if not os.path.exists("logs"): os.makedirs("logs")
        ruta = os.path.join("logs", f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        self.log_file = open(ruta, "a")
        print(f"[✔] Sesión iniciada: {ruta}")

    def enviar_comando_dinamico(self, v, a, d, g):
        cmd = f"V:{v:.1f},A:{a:.1f},D:{d:.1f},G:{g:.2f}\n"
        self.conexion.write(cmd.encode('utf-8'))
        res = self.conexion.readline().decode('utf-8').strip() or "TIMEOUT"
        ts = datetime.now().strftime("%H:%M:%S")
        info = f"[{ts}] Ang:{g:>6.1f}º | V:{v:>4.0f} | A:{a:>4.0f} | D:{d:>4.0f} -> [STM32]: {res}"
        print(f"-> {info}")
        if self.log_file: 
            self.log_file.write(info + "\n")
            self.log_file.flush()

    def comando_enviar_kvals(self):
        if self.entrenando: 
            return print("[!] Detén el ciclo para ajustar los KVALs.")
        if not self.conectar_serial(): 
            return
        try:
            kh = int(self.entry_khold.get())
            kr = int(self.entry_krun.get())
            ka = int(self.entry_kacc.get())
            kd = int(self.entry_kdec.get())
            
            # Validación por porcentaje
            if any(val < 0 or val > 100 for val in [kh, kr, ka, kd]):
                return print("[!] Error: Los KVALs deben estar entre 0% y 100%.")

            cmd = f"K:{kh},{kr},{ka},{kd}\n"
            print(f"[...] Configurando Potencia Motor -> {cmd.strip()}%")
            self.conexion.write(cmd.encode())
            res = self.conexion.readline().decode('utf-8').strip()
            print(f"[✔] [STM32]: {res}")
            
        except ValueError:
            print("[!] Error: Asegúrate de introducir números enteros (0-100) en los KVALs.")

    def comando_homing(self):
        if self.entrenando: return print("[!] Detén el ciclo antes de Homing.")
        if not self.conectar_serial(timeout=12.0): return
        if not self.log_file: self.inicializar_log()
        print("[...] Ejecutando Homing...")
        self.conexion.write(b"HOME\n")
        res = self.conexion.readline().decode('utf-8').strip()
        self.conexion.timeout = 1.0
        print(f"[✔] [STM32]: {res}")
        self.log_file.write(f"[{datetime.now()}] Homing: {res}\n")
        self.log_file.flush()

    def comando_start(self):
        if self.entrenando or not self.conectar_serial(): return
        if not self.log_file: self.inicializar_log()
        self.entrenando = True
        self.hilo_entrenamiento = threading.Thread(target=self.rutina_entrenamiento, daemon=True)
        self.hilo_entrenamiento.start()

    def comando_finish(self):
        if self.entrenando:
            self.entrenando = False
            print("[...] Pidiendo parada segura...")

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
                for _ in range(int(espera * 10)):
                    if not self.entrenando: break
                    time.sleep(0.1)
        except Exception as e: print(f"[!] Error en rutina: {e}")
        self.entrenando = False
        print("[✔] Entrenamiento detenido.")

    def cerrar_aplicacion(self):
        self.guardar_configuracion()
        self.entrenando = False
        if self.conexion: self.conexion.close()
        if self.log_file: self.log_file.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorGUI(root)
    root.mainloop()