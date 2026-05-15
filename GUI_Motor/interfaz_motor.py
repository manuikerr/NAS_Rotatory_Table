import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import serial
import serial.tools.list_ports
import time
import random
import os
import json
from datetime import datetime
import threading
import sys
from PIL import Image
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import subprocess

if hasattr(sys, '_MEIPASS'):
    # Si es un .exe, la raíz es la carpeta temporal de PyInstaller
    RUTA_BASE = sys._MEIPASS
else:
    # Si es un script .py, la raíz es la carpeta donde está el archivo
    RUTA_BASE = os.path.dirname(os.path.abspath(__file__))

def obtener_ruta_recurso(nombre_archivo):
    """Accede a la carpeta centralizada de imágenes assets/img/"""
    return os.path.join(RUTA_BASE, "assets", "img", nombre_archivo)

# Configuración global del tema de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =============================================================================
# CLASE TOOLTIP (Hover Info)
# =============================================================================
# =============================================================================
# CLASE TOOLTIP (Hover Info con Detección de Bordes)
# =============================================================================
class ToolTip:
    """Crea un pequeño globo de información al pasar el ratón sobre un widget."""
    def __init__(self, widget, text):
        """Inicializa el ToolTip enlazándolo a los eventos del ratón del widget especificado."""
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        
        # CTkWidgets a veces necesitan vincularse a su componente interno
        if hasattr(widget, "_canvas"): 
            self.widget._canvas.bind("<Enter>", self.enter)
            self.widget._canvas.bind("<Leave>", self.leave)
            if hasattr(widget, "_text_label"):
                self.widget._text_label.bind("<Enter>", self.enter)
                self.widget._text_label.bind("<Leave>", self.leave)
        else:
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        """Muestra la ventana emergente calculando si colisiona con los bordes del monitor."""
        if self.tooltip_window or not self.text: return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 30
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        
        bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"
        fg = "white" if ctk.get_appearance_mode() == "Dark" else "black"
        
        tk.Label(tw, text=self.text, justify='left', background=bg, fg=fg, 
                 relief='solid', borderwidth=1, font=("Arial", 10), padx=5, pady=3).pack()

        tw.update_idletasks()
        ancho_tooltip = tw.winfo_reqwidth()
        ancho_pantalla = self.widget.winfo_screenwidth()

        if (x + ancho_tooltip) > ancho_pantalla:
            x = ancho_pantalla - ancho_tooltip - 15

        tw.wm_geometry(f"+{x}+{y}")

    def leave(self, event=None):
        """Destruye el globo de información cuando el ratón sale del área del widget."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# =============================================================================
# UTILIDADES GLOBALES
# =============================================================================
def obtener_timestamp():
    """Genera una marca de tiempo con resolución de milisegundos para los logs."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

# =============================================================================
# REDIRECCIÓN DE CONSOLA
# =============================================================================
class ConsoleRedirector:
    """Intercepta los comandos 'print' de Python, bifurcando la salida a GUI y archivos."""
    def __init__(self, app, func_log, btn_scroll):
        """Prepara el interceptor enlazando referencias a la app principal y funciones de log."""
        self.app = app
        self.text_widget = app.consola
        self.func_log = func_log
        self.btn_scroll = btn_scroll

    def write(self, message):
        """Intercepción primaria de sys.stdout, envía el mensaje a la interfaz y al archivo."""
        self.text_widget.after(0, self._write, message)
        self.func_log(message)

    def _write(self, message):
        """Lógica para insertar texto en consola principal y flotante manteniendo smart-scroll."""
        # Escritura en la consola principal
        self.text_widget.configure(state='normal')
        y_scroll = self.text_widget._textbox.yview()[1]
        at_bottom = y_scroll >= 0.98
        self.text_widget.insert(tk.END, message)
        
        if at_bottom:
            self.text_widget.see(tk.END)
            self.btn_scroll.place_forget()
        elif message.strip():
            self.btn_scroll.place(relx=0.99, rely=0.95, anchor="se")
            
        self.text_widget.configure(state='disabled')

        # Reflejo en consola flotante (si existe)
        if hasattr(self.app, 'top_consola') and self.app.top_consola and self.app.top_consola.winfo_exists():
            flotante = self.app.consola_flotante
            btn_float = self.app.btn_scroll_flotante
            flotante.configure(state='normal')
            
            y_scroll_f = flotante._textbox.yview()[1]
            at_bottom_f = y_scroll_f >= 0.98
            flotante.insert(tk.END, message)
            
            if at_bottom_f:
                flotante.see(tk.END)
                btn_float.place_forget()
            elif message.strip():
                btn_float.place(relx=0.99, rely=0.95, anchor="se")
                
            flotante.configure(state='disabled')

    def flush(self): 
        """Requisito obligatorio de la interfaz sys.stdout de Python."""
        pass

# =============================================================================
# CAPA DE LÓGICA Y HARDWARE
# =============================================================================
class MotorControl:
    """Gestiona la comunicación Serial con el STM32, hilos de ejecución y data logging."""
    
    SIMULADOR_ID = "MODO_TEST"
    MSG_ANGULO_OK = "Angulo recibido"
    MSG_TIMEOUT = "TIMEOUT"

    def __init__(self, cb_conn, cb_motor, cb_progreso, cb_grafica):
        """Inicializa los callbacks de comunicación con la capa visual GUI."""
        self.cb_conn = cb_conn          
        self.cb_motor = cb_motor        
        self.cb_progreso = cb_progreso  
        self.cb_grafica = cb_grafica
        
        self.conexion = None
        self.log_file = None
        self.entrenando = False
        self.hilo_entrenamiento = None
        
        self.rutina_csv = []
        self.movimientos_count = 0

    def inicializar_log(self):
        """Crea el archivo físico de registro de telemetría en disco."""
        ruta_script = os.path.dirname(os.path.abspath(__file__))
        carpeta_logs = os.path.join(ruta_script, "logs")
        if not os.path.exists(carpeta_logs):
            os.makedirs(carpeta_logs)
            
        nombre_archivo = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ruta_completa_log = os.path.join(carpeta_logs, nombre_archivo)
        
        print(f"[DEBUG] Guardando log en: {ruta_completa_log}")
        self.log_file = open(ruta_completa_log, "a", encoding="utf-8")

    def reset_log(self):
        """Cierra el archivo actual y fuerza la creación de uno nuevo."""
        if getattr(self, 'log_file', None) and not getattr(self.log_file, 'closed', True):
            try:
                self.escribir_log("\n[INFO] --- CIERRE DE LOG ACTUAL. ABRIENDO NUEVO ARCHIVO ---\n")
                self.log_file.close()
            except Exception: pass
        
        self.log_file = None
        self.inicializar_log()
        print("[INFO] Se ha generado un nuevo archivo de registro .txt")

    def escribir_log(self, mensaje):
        """Agrega de forma segura un nuevo mensaje físico al archivo .txt abierto."""
        if getattr(self, 'log_file', None) and not getattr(self.log_file, 'closed', True):
            try:
                self.log_file.write(mensaje)
                self.log_file.flush()
            except Exception:
                pass

    def obtener_puertos(self):
        """Realiza un barrido del sistema operativo para listar los puertos COM disponibles."""
        return [p.device for p in serial.tools.list_ports.comports()]

    def conectar_serial(self, puerto, baud, es_simulador, timeout=1.0):
        """Abre el puerto físico serial o engancha el modo simulador bypass."""
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
        """Envía el comando de calibración de potencia eléctrica L6470."""
        cmd = f"K:{kh},{kr},{ka},{kd}\n"
        print(f"[PC] Enviando configuración KVALs: {cmd.strip()}")            
        
        if self.conexion == self.SIMULADOR_ID:
            res = f"KVAL OK -> HOLD:{kh}% RUN:{kr}% ACC:{ka}% DEC:{kd}%"
        else:
            self.conexion.write(cmd.encode())
            res = self.conexion.readline().decode('utf-8').strip()
            
        print(f"[✔] [STM32]: {res}")

    def ejecutar_homing(self):
        """Lanza el proceso de Homing en un hilo separado para no bloquear la UI."""
        threading.Thread(target=self._hilo_homing, daemon=True).start()

    def _hilo_homing(self):
        """Lógica interna de Homing ejecutada en segundo plano."""
        print(f"[{obtener_timestamp()}] [PC] Ejecutando rutina de Homing...")
        self.cb_motor("HOMING")
        
        try:
            if self.conexion == self.SIMULADOR_ID:
                time.sleep(2)
                res = "Homing completado (Simulado)"
            else:
                self.conexion.write(b"HOME\n")
                res = self.conexion.readline().decode('utf-8').strip()
            
            print(f"[{obtener_timestamp()}] [✔] [STM32]: {res}")
        except Exception as e:
            print(f"[!] Error en Homing: {e}")
        finally:
            self.cb_motor("REPOSO")

    def iniciar_entrenamiento(self, horas, espera, cfg):
        """Prepara e inicia el sub-proceso (thread) del bucle de movimientos continuos."""
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
        """Hilo secundario. Calcula y manda parámetros cíclica o aleatoriamente hasta la detención."""
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
                
                self.cb_grafica(v, a, d)

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
        """Formatea y escribe la trama completa V-A-D-G hacia el microcontrolador STM32."""
        cmd = f"V:{v:.1f},A:{a:.1f},D:{d:.1f},G:{g:.2f}\n"
        
        if self.conexion == self.SIMULADOR_ID:
            time.sleep(0.05)
            res = self.MSG_ANGULO_OK
        else:
            self.conexion.write(cmd.encode('utf-8'))
            res = self.conexion.readline().decode('utf-8').strip() or self.MSG_TIMEOUT
            
        print(f"[{obtener_timestamp()}] [PC] Ang:{g:>6.1f}º | V:{v:>4.0f} | A:{a:>4.0f} | D:{d:>4.0f} | -> [STM32]: {res}")

    def detener_entrenamiento(self):
        """Cambia el estado lógico deteniendo de manera segura el hilo de envíos."""
        if self.entrenando:
            self.entrenando = False
            print(f"[{obtener_timestamp()}] [PC] SOFT STOP: Pidiendo parada segura...")

    def cerrar_conexion(self):
        """Cierra el puerto físico USB del STM32 y archiva los archivos .txt de log."""
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
    """Gestiona exclusivamente el renderizado y los eventos visuales usando CustomTkinter."""
    
    def __init__(self, root):
        """Constructor principal de la ventana y variables persistentes base."""
        self.root = root
        self.root.title("Panel de Control - Mesa Rotatoria STM32")
        self.root.geometry("1150x800")
        self.root.minsize(1050, 750)
        
        # La ruta base para config.json sigue siendo la raíz del script
        self.ruta_base = RUTA_BASE 
        self.archivo_config = os.path.join(self.ruta_base, "config.json")    

# El icono ahora se busca en assets/img/
        ruta_icono = obtener_ruta_recurso("icofinal.ico")
        if os.path.exists(ruta_icono):
            self.root.after(200, lambda: self.root.iconbitmap(ruta_icono))
        
        self._aplicar_tema_guardado()

        self.motor = MotorControl(
            cb_conn=self.actualizar_led_conexion,
            cb_motor=self.actualizar_led_motor,
            cb_progreso=self.actualizar_progreso_ui,
            cb_grafica=self.actualizar_grafica_hilo
        )

        self.crear_interfaz()
        self.cargar_configuracion()

        self.root.after(0, lambda: self.root.state('zoomed'))
        
        sys.stdout = ConsoleRedirector(self, self.motor.escribir_log, self.btn_scroll_down)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)
        
        self.actualizar_grafica()

    def _aplicar_tema_guardado(self):
        """Carga en pre-ejecución el tema oscuro/claro y el color elegido anteriormente."""
        apariencia = "Dark"
        color_tema = "blue"
        if os.path.exists(self.archivo_config):
            try:
                with open(self.archivo_config, 'r') as f:
                    c = json.load(f)
                    apariencia = c.get("apariencia", "Dark")
                    color_tema = c.get("color_tema", "blue")
            except Exception: pass
        
        ctk.set_appearance_mode(apariencia)
        try: ctk.set_default_color_theme(color_tema)
        except Exception: pass

    def _preparar_icono(self, ruta_archivo, color_hex=None):
        """Trata y escala imágenes PNG desde assets/img/ para botones."""
        try:
            full_path = obtener_ruta_recurso(ruta_archivo)
            img = Image.open(full_path).convert("RGBA")
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            if color_hex:
                color_hex = color_hex.lstrip('#')
                rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                r, g, b, a = img.split()
                img = Image.merge("RGBA", (
                    r.point(lambda _: rgb[0]), 
                    r.point(lambda _: rgb[1]), 
                    r.point(lambda _: rgb[2]), 
                    a
                ))
            return ctk.CTkImage(light_image=img, dark_image=img, size=(16, 16))
            
        except Exception as e:
            print(f"Error cargando icono {ruta_archivo}: {e}")
            return None

    def abrir_carpeta_logs(self):
        """Abre el explorador de archivos en la carpeta de registros del sistema."""
        ruta_logs = os.path.join(self.ruta_base, "logs")
        
        if not os.path.exists(ruta_logs):
            os.makedirs(ruta_logs)
            
        # Comando nativo de Windows para abrir la carpeta
        subprocess.Popen(['explorer', os.path.normpath(ruta_logs)], shell=True)
        print(f"[INFO] Abriendo explorador en: {ruta_logs}")

    def comando_nuevo_log(self):
        """Acción del botón para forzar un nuevo archivo de registro."""
        self.motor.reset_log()

    def crear_interfaz(self):
        """Renderizado estructural masivo del dashboard principal con distancias uniformes."""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1) 

        self.iconos = {
            'home': self._preparar_icono("botonHome.png", "FFFFFF"),
            'play': self._preparar_icono("botonPlay.png", "FFFFFF"),
            'stop': self._preparar_icono("botonStop.png", "FFFFFF"),
            'quit': self._preparar_icono("botonQuit.png", "FFFFFF"),
            'borrar': self._preparar_icono("botonBorrarCSV.png", "FFFFFF")
        }

        # --- ENCABEZADO ---
        frame_encabezado = ctk.CTkFrame(self.root, fg_color="transparent")
        frame_encabezado.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        frame_encabezado.columnconfigure(2, weight=1) 

        # Logos
        try:
            ruta_logo_etsii = obtener_ruta_recurso("logo-ETSII-US-Horizontal-Color.png")
            img_etsii_us = Image.open(ruta_logo_etsii)
            ancho_proporcional = int(img_etsii_us.size[0] * 45 / img_etsii_us.size[1])
            img_ctk_etsii_us = ctk.CTkImage(light_image=img_etsii_us, dark_image=img_etsii_us, size=(ancho_proporcional, 45))
            ctk.CTkLabel(frame_encabezado, image=img_ctk_etsii_us, text="").grid(row=0, column=0, sticky="w")
            
        except Exception:
            ctk.CTkLabel(frame_encabezado, text="[LOGOS]", font=ctk.CTkFont(weight="bold"), fg_color="gray30", corner_radius=8).grid(row=0, column=0, columnspan=2, sticky="w")

        # Selectores de Tema
        frame_temas = ctk.CTkFrame(frame_encabezado, fg_color="transparent")
        frame_temas.grid(row=0, column=2, sticky="e")
        
        ctk.CTkLabel(frame_temas, text="Tema:", font=ctk.CTkFont(size=12)).pack(side=tk.LEFT, padx=(0, 5))
        self.opcion_apariencia = ctk.CTkOptionMenu(frame_temas, values=["Dark", "Light", "System"], command=self.cambiar_apariencia, width=90, height=24)
        self.opcion_apariencia.pack(side=tk.LEFT, padx=(0, 15))

        ctk.CTkLabel(frame_temas, text="Color:", font=ctk.CTkFont(size=12)).pack(side=tk.LEFT, padx=(0, 5))
        self.opcion_color = ctk.CTkOptionMenu(frame_temas, values=["blue", "green", "dark-blue"], command=self.cambiar_color, width=90, height=24)
        self.opcion_color.pack(side=tk.LEFT)

        # Créditos
        txt_creditos = "Desarrollado por:\nÁngel Francisco Jiménez Fernández & Manuel Martín Aguaded"
        ctk.CTkLabel(frame_encabezado, text=txt_creditos, justify=tk.RIGHT, font=ctk.CTkFont(size=11, slant="italic"), text_color="gray50").grid(row=0, column=3, sticky="e", padx=(20, 0))

        # --- PANEL SUPERIOR: CONFIGURACIÓN Y ESTADÍSTICAS ---
        frame_top = ctk.CTkFrame(self.root, fg_color="transparent")
        frame_top.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        frame_top.columnconfigure(0, weight=3)
        frame_top.columnconfigure(1, weight=1)

        # Configuración del Sistema
        frame_config = ctk.CTkFrame(frame_top, corner_radius=8)
        frame_config.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(frame_config, text="Configuración del Sistema", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=9, sticky="w", padx=15, pady=(10, 10))

        ctk.CTkLabel(frame_config, text="Puerto:").grid(row=1, column=0, sticky="w", padx=(15, 5), pady=(0, 15))
        self.combo_puertos = ctk.CTkComboBox(frame_config, values=self.motor.obtener_puertos(), width=130)
        self.combo_puertos.grid(row=1, column=1, padx=5, pady=(0, 15))
        
        ctk.CTkLabel(frame_config, text="Baud:").grid(row=1, column=2, padx=(10, 5), pady=(0, 15))
        self.entry_baud = ctk.CTkEntry(frame_config, width=80)
        self.entry_baud.grid(row=1, column=3, padx=5, pady=(0, 15))

        ctk.CTkLabel(frame_config, text="Horas:").grid(row=1, column=4, padx=(10, 5), pady=(0, 15))
        self.entry_horas = ctk.CTkEntry(frame_config, width=70)
        self.entry_horas.grid(row=1, column=5, padx=5, pady=(0, 15))

        ctk.CTkLabel(frame_config, text="Pausa(s):").grid(row=1, column=6, padx=(10, 5), pady=(0, 15))
        self.entry_espera = ctk.CTkEntry(frame_config, width=70)
        self.entry_espera.grid(row=1, column=7, padx=5, pady=(0, 15))

        self.var_simulador = tk.BooleanVar(value=False)
        self.sw_simulador = ctk.CTkSwitch(frame_config, text="Simulador", variable=self.var_simulador, command=self.toggle_simulador, progress_color="#8a2be2")
        self.sw_simulador.grid(row=1, column=8, padx=(15, 15), pady=(0, 15))
        ToolTip(self.sw_simulador, "Activa el entorno virtual sin necesidad de conectar hardware real.")

        # Estadísticas
        frame_progreso = ctk.CTkFrame(frame_top, corner_radius=8, fg_color=("gray85", "gray16"))
        frame_progreso.grid(row=0, column=1, sticky="nsew")
        frame_progreso.columnconfigure(0, weight=1)
        frame_progreso.columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_progreso, text="Estadísticas", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        # --- SUB-FRAME PARA BOTONES DE LOG ---
        frame_botones_log = ctk.CTkFrame(frame_progreso, fg_color="transparent")
        frame_botones_log.grid(row=0, column=1, sticky="e", padx=15, pady=(10, 5))

        self.btn_nuevo_log = ctk.CTkButton(
            frame_botones_log, 
            text="Nuevo Log", 
            width=65, 
            height=22, 
            fg_color="#2b2b2b", 
            border_width=1, 
            border_color="gray50",
            hover_color="#3b3b3b",
            font=ctk.CTkFont(size=11),
            command=self.comando_nuevo_log
        )
        self.btn_nuevo_log.pack(side="left", padx=2)
        ToolTip(self.btn_nuevo_log, "Finaliza el log actual y genera uno nuevo para el siguiente ensayo")

        self.btn_abrir_logs = ctk.CTkButton(
            frame_botones_log, 
            text="Ver Logs", 
            width=65,    
            height=22, 
            fg_color="#2b2b2b", 
            border_width=1, 
            border_color="gray50",
            hover_color="#3b3b3b",
            font=ctk.CTkFont(size=11),
            command=self.abrir_carpeta_logs
        )
        self.btn_abrir_logs.pack(side="left", padx=2) 
        ToolTip(self.btn_abrir_logs, "Abre la carpeta local de registros .txt")

        self.label_movimientos = ctk.CTkLabel(frame_progreso, text="Movs: 0", font=ctk.CTkFont(size=14, weight="bold"))
        self.label_movimientos.grid(row=1, column=0, sticky="w", padx=20, pady=(5, 15))

        self.label_reloj = ctk.CTkLabel(frame_progreso, text="⌛ 00:00:00", font=ctk.CTkFont(family="Consolas", size=15, weight="bold"), text_color="#1f6aa5")
        self.label_reloj.grid(row=1, column=1, sticky="e", padx=20, pady=(5, 15))

        # --- PANEL CENTRAL: PARÁMETROS MOTOR, KVALS Y GRÁFICA ---
        frame_motor_master = ctk.CTkFrame(self.root, fg_color="transparent")
        frame_motor_master.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        frame_motor_master.columnconfigure(0, weight=1, uniform="group1")
        frame_motor_master.columnconfigure(1, weight=1, uniform="group1")

        # Movimiento (Columna Izquierda)
        frame_motor = ctk.CTkFrame(frame_motor_master, corner_radius=8)
        frame_motor.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(frame_motor, text="Parámetros de Movimiento", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 10))

        self.var_rand_ang = tk.BooleanVar(value=True)
        self.var_rand_vel = tk.BooleanVar(value=True)
        self.var_rand_acc = tk.BooleanVar(value=True)
        self.var_rand_dec = tk.BooleanVar(value=True)
        self.var_link_acc_dec = tk.BooleanVar(value=True)
        
        ancho_lbl = 40
        ancho_ent = 80

        def on_entry_change(event=None):
            self.actualizar_grafica()

        ctk.CTkCheckBox(frame_motor, text="Ángulo Aleatorio (-180 a 180)", variable=self.var_rand_ang, command=self.cb_movimiento).grid(row=1, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkLabel(frame_motor, text="Fijo:", width=ancho_lbl, anchor="e").grid(row=1, column=1, padx=(10, 5), sticky="e")
        self.entry_ang = ctk.CTkEntry(frame_motor, width=ancho_ent)
        self.entry_ang.grid(row=1, column=2, padx=(0, 15), sticky="w")

        ctk.CTkCheckBox(frame_motor, text="Velocidad Aleatoria (200 a 800)", variable=self.var_rand_vel, command=self.cb_movimiento).grid(row=2, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkLabel(frame_motor, text="Fijo:", width=ancho_lbl, anchor="e").grid(row=2, column=1, padx=(10, 5), sticky="e")
        self.entry_vel = ctk.CTkEntry(frame_motor, width=ancho_ent)
        self.entry_vel.grid(row=2, column=2, padx=(0, 15), sticky="w")
        self.entry_vel.bind("<KeyRelease>", on_entry_change)

        ctk.CTkCheckBox(frame_motor, text="Aceleración Aleatoria (800 a 4000)", variable=self.var_rand_acc, command=self.cb_movimiento).grid(row=3, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkLabel(frame_motor, text="Fijo:", width=ancho_lbl, anchor="e").grid(row=3, column=1, padx=(10, 5), sticky="e")
        self.entry_acc = ctk.CTkEntry(frame_motor, width=ancho_ent)
        self.entry_acc.grid(row=3, column=2, padx=(0, 15), sticky="w")
        self.entry_acc.bind("<KeyRelease>", on_entry_change)

        self.check_rand_dec = ctk.CTkCheckBox(frame_motor, text="Desaceleración Aleat. (800 a 4000)", variable=self.var_rand_dec, command=self.cb_movimiento)
        self.check_rand_dec.grid(row=4, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkLabel(frame_motor, text="Fijo:", width=ancho_lbl, anchor="e").grid(row=4, column=1, padx=(10, 5), sticky="e")
        self.entry_dec = ctk.CTkEntry(frame_motor, width=ancho_ent)
        self.entry_dec.grid(row=4, column=2, padx=(0, 15), sticky="w")
        self.entry_dec.bind("<KeyRelease>", on_entry_change)

        ctk.CTkSwitch(frame_motor, text="🔗 Vincular Acc/Dec (Simétrico)", variable=self.var_link_acc_dec, command=self.cb_movimiento).grid(row=5, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 5))

        # Espaciado uniforme para CSV
        ctk.CTkFrame(frame_motor, height=2, fg_color=("gray80", "gray30")).grid(row=6, column=0, columnspan=3, sticky="ew", padx=15, pady=(10, 10))

        # Panel CSV
        frame_csv = ctk.CTkFrame(frame_motor, fg_color="transparent")
        frame_csv.grid(row=7, column=0, columnspan=3, sticky="w", padx=10, pady=0)

        self.var_ciclico_csv = tk.BooleanVar(value=True)
        self.sw_ciclico = ctk.CTkSwitch(frame_csv, text="Cíclico", variable=self.var_ciclico_csv, width=60)
        self.sw_ciclico.pack(side=tk.LEFT, padx=10)
        ToolTip(self.sw_ciclico, "Repite el archivo CSV cíclicamente hasta que se acabe el tiempo 'Horas'.")

        ctk.CTkButton(frame_csv, text="Cargar CSV", command=self.comando_cargar_csv, fg_color="#2b2b2b", hover_color="#3b3b3b", border_width=1, border_color="gray50", width=100).pack(side=tk.LEFT, padx=(5, 0))
        
        self.iconos['borrar'].configure(size=(12, 12))
        self.btn_borrar_csv = ctk.CTkButton(frame_csv, text="", image=self.iconos['borrar'], width=26, height=26, command=self.borrar_rutina_csv, fg_color="#cc0000", hover_color="#ff3333", state="disabled", anchor="center")
        self.btn_borrar_csv.pack(side=tk.LEFT, padx=5)

        self.label_csv = ctk.CTkLabel(frame_csv, text="Modo: Aleatorio/Fijo", font=ctk.CTkFont(size=11, slant="italic"), text_color="gray50")
        self.label_csv.pack(side=tk.LEFT, padx=10)

        # -------------------------------------------------------------
        # NUEVO BLOQUE: Estado y Comandos integrados debajo de los parámetros
        # -------------------------------------------------------------
        ctk.CTkFrame(frame_motor, height=2, fg_color=("gray80", "gray30")).grid(row=8, column=0, columnspan=3, sticky="ew", padx=15, pady=(10, 10))

        frame_estado_cmd = ctk.CTkFrame(frame_motor, fg_color="transparent")
        frame_estado_cmd.grid(row=9, column=0, columnspan=3, sticky="nsew", padx=15, pady=(0, 15))
        frame_estado_cmd.columnconfigure(0, weight=1)
        frame_estado_cmd.columnconfigure(1, weight=1)

        # Estado Motor
        frame_estado = ctk.CTkFrame(frame_estado_cmd, fg_color="transparent")
        frame_estado.grid(row=0, column=0, sticky="nw")
        ctk.CTkLabel(frame_estado, text="Estado Motor", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray50").pack(anchor="w", pady=(0, 5))
        
        self.led_conexion = ctk.CTkLabel(frame_estado, text="🔴 DESCONECTADO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#cc0000")
        self.led_conexion.pack(anchor="w", pady=2)
        self.led_motor = ctk.CTkLabel(frame_estado, text="⚪ MOTOR: REPOSO", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60")
        self.led_motor.pack(anchor="w", pady=2)

        # Comandos
        frame_cmds = ctk.CTkFrame(frame_estado_cmd, fg_color="transparent")
        frame_cmds.grid(row=0, column=1, sticky="ne", padx=(25, 0))
        ctk.CTkLabel(frame_cmds, text="Comandos", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray50").grid(row=0, column=0, columnspan=4, sticky="e", pady=(0, 5))

        # Distribución horizontal de los 4 botones
        btn_home = ctk.CTkButton(frame_cmds, text="HOMING", image=self.iconos['home'], command=self.comando_homing, fg_color="#1f6aa5", hover_color="#144870", width=85, height=28, font=ctk.CTkFont(weight="bold"))
        btn_home.grid(row=1, column=0, padx=2, pady=2)
        ToolTip(btn_home, "Calibra el motor buscando el punto 0 físico (sensor origen).")

        icono_start = self.iconos['play']
        icono_start.configure(size=(13, 13)) # Ajuste fino para que no se vea gigante
        
        btn_start = ctk.CTkButton(frame_cmds, text="START", image=icono_start, command=self.comando_start, fg_color="#28a745", hover_color="#1e7e34", width=85, height=28, font=ctk.CTkFont(weight="bold"))
        btn_start.grid(row=1, column=1, padx=2, pady=2)
        ToolTip(btn_start, "Inicia la rutina cíclica con los parámetros configurados.")

        icono_stop = self.iconos['stop']
        icono_stop.configure(size=(12, 12))
        
        btn_stop = ctk.CTkButton(frame_cmds, text="S. STOP", image=icono_stop, command=self.comando_soft_stop, fg_color="#fd7e14", hover_color="#d3640b", width=85, height=28, font=ctk.CTkFont(weight="bold"))
        btn_stop.grid(row=1, column=2, padx=2, pady=2)
        ToolTip(btn_stop, "Pide al STM32 detenerse progresivamente de forma segura.")

        btn_quit = ctk.CTkButton(frame_cmds, text="QUIT", image=self.iconos['quit'], command=self.cerrar_aplicacion, fg_color="#dc3545", hover_color="#a71d2a", width=85, height=28, font=ctk.CTkFont(weight="bold"))
        btn_quit.grid(row=1, column=3, padx=2, pady=2)
        ToolTip(btn_quit, "Cierra el puerto serie, guarda la configuración y sale.")

        # 2. K-Values y Gráfica (Columna Derecha)
        frame_right_container = ctk.CTkFrame(frame_motor_master, fg_color="transparent")
        frame_right_container.grid(row=0, column=1, sticky="nsew")

        # K-Values
        frame_kval = ctk.CTkFrame(frame_right_container, corner_radius=8)
        frame_kval.pack(fill=tk.X, pady=(0, 10)) 

        ctk.CTkLabel(frame_kval, text="K_Values (Potencia: 0% - 100%)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(10, 10))
        
        ancho_k_lbl = 50
        ancho_k_ent = 70

        ctk.CTkLabel(frame_kval, text="HOLD:", width=ancho_k_lbl, anchor="e").grid(row=1, column=0, padx=(15, 5), pady=5, sticky="e")
        self.entry_khold = ctk.CTkEntry(frame_kval, width=ancho_k_ent)
        self.entry_khold.grid(row=1, column=1, padx=(0, 15), pady=5, sticky="w")
        
        ctk.CTkLabel(frame_kval, text="RUN:", width=ancho_k_lbl, anchor="e").grid(row=1, column=2, padx=(15, 5), pady=5, sticky="e")
        self.entry_krun = ctk.CTkEntry(frame_kval, width=ancho_k_ent)
        self.entry_krun.grid(row=1, column=3, padx=(0, 15), pady=5, sticky="w")

        ctk.CTkLabel(frame_kval, text="ACC:", width=ancho_k_lbl, anchor="e").grid(row=2, column=0, padx=(15, 5), pady=5, sticky="e")
        self.entry_kacc = ctk.CTkEntry(frame_kval, width=ancho_k_ent)
        self.entry_kacc.grid(row=2, column=1, padx=(0, 15), pady=5, sticky="w")

        ctk.CTkLabel(frame_kval, text="DEC:", width=ancho_k_lbl, anchor="e").grid(row=2, column=2, padx=(15, 5), pady=5, sticky="e")
        self.entry_kdec = ctk.CTkEntry(frame_kval, width=ancho_k_ent)
        self.entry_kdec.grid(row=2, column=3, padx=(0, 15), pady=5, sticky="w")

        ctk.CTkButton(frame_kval, text="⚡ APLICAR KVALS", command=self.comando_enviar_kvals, fg_color="#8b8000", hover_color="#a89b00", text_color="white", corner_radius=6).grid(row=3, column=0, columnspan=4, padx=20, pady=(15, 15), sticky="ew")

        # Gráfica Perfil Trapezoidal Pop-Out
        self.frame_grafica = ctk.CTkFrame(frame_right_container, corner_radius=8)
        self.frame_grafica.pack(fill=tk.BOTH, expand=True)
        
        header_grafica = ctk.CTkFrame(self.frame_grafica, fg_color="transparent")
        header_grafica.pack(fill=tk.X, padx=10, pady=(10, 0))
        ctk.CTkLabel(header_grafica, text="Perfil de Velocidad", font=ctk.CTkFont(size=12, weight="bold")).pack(side=tk.LEFT)
        ctk.CTkButton(header_grafica, text="⤢", width=28, height=24, fg_color="#444", hover_color="#555", command=self.abrir_grafica_flotante).pack(side=tk.RIGHT)
        ToolTip(header_grafica.winfo_children()[1], "Abrir gráfica en ventana flotante")

        self.fig = Figure(figsize=(4, 2.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_grafica)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # --- PANEL INFERIOR (Solo Consola) ---
        frame_inferior_master = ctk.CTkFrame(self.root, fg_color="transparent")
        frame_inferior_master.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        frame_inferior_master.columnconfigure(0, weight=1)
        frame_inferior_master.rowconfigure(0, weight=1)

        # Consola Expandida Pop-Out
        frame_consola = ctk.CTkFrame(frame_inferior_master, corner_radius=8)
        frame_consola.grid(row=0, column=0, sticky="nsew")
        
        header_consola = ctk.CTkFrame(frame_consola, fg_color="transparent")
        header_consola.pack(fill=tk.X, padx=15, pady=(5, 0))
        ctk.CTkLabel(header_consola, text="Consola de Telemetría (Real-time)", font=ctk.CTkFont(size=12, weight="bold")).pack(side=tk.LEFT)
        ctk.CTkButton(header_consola, text="⤢", width=28, height=24, fg_color="#444", hover_color="#555", command=self.abrir_consola_flotante).pack(side=tk.RIGHT)
        ToolTip(header_consola.winfo_children()[1], "Abrir consola en ventana flotante")

        self.consola = ctk.CTkTextbox(frame_consola, fg_color="#0c0c0c", text_color="#33ff33", font=ctk.CTkFont(family="Consolas", size=12), state='disabled', wrap="word")
        self.consola.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # Botón de scroll para la consola principal anclado dentro de la consola
        self.btn_scroll_down = ctk.CTkButton(self.consola, text="⬇", width=30, height=30, fg_color="#444", hover_color="#555", corner_radius=6, command=self._scroll_to_bottom)

        # Bindings para chequear scroll manual en la consola principal
        self.consola._textbox.bind("<MouseWheel>", self._check_scroll)
        self.consola._textbox.bind("<B1-Motion>", self._check_scroll)
        self.consola._textbox.bind("<ButtonRelease-1>", self._check_scroll)

    # =============================================================================
    # MÉTODOS DE UI Y GRÁFICA
    # =============================================================================
    def cb_movimiento(self):
        """Actualiza estados de bloqueos manuales e hila los gráficos dinámicamente."""
        self.toggle_entries()
        self.actualizar_grafica()

    def actualizar_grafica_hilo(self, v_in, a_in, d_in):
        """Callback seguro para que el hilo de entrenamiento actualice la gráfica."""
        self.root.after(0, self.actualizar_grafica, v_in, a_in, d_in)

    def actualizar_grafica(self, v_in=None, a_in=None, d_in=None):
        """Dibuja el perfil de velocidad trapezoidal resolviendo el color RGBA nativo."""
        self.ax.clear()

        # Adaptación de colores al tema
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#2b2b2b" if is_dark else "#dbdbdb"
        text_color = "white" if is_dark else "black"

        # Aplicamos colores a la figura de Matplotlib principal
        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        self.ax.tick_params(colors=text_color, labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(text_color)

        if v_in is not None and a_in is not None and d_in is not None:
            v, a, d = v_in, a_in, d_in
        else:
            try:
                v = float(self.entry_vel.get()) if self.entry_vel.get() and not self.var_rand_vel.get() else 500.0
                a = float(self.entry_acc.get()) if self.entry_acc.get() and not self.var_rand_acc.get() else 1000.0
                d = float(self.entry_dec.get()) if self.entry_dec.get() and not self.var_rand_dec.get() else 1000.0
                if self.var_link_acc_dec.get(): 
                    d = a
            except (ValueError, AttributeError):
                v, a, d = 500.0, 1000.0, 1000.0

        if a <= 0: a = 1
        if d <= 0: d = 1

        t_a = v / a
        t_d = v / d
        t_const = 0.4 

        tiempos = [0, t_a, t_a + t_const, t_a + t_const + t_d]
        velocidades = [0, v, v, 0]

        # Renderizado en ventana base
        self.ax.plot(tiempos, velocidades, color="#1f6aa5", linewidth=2)
        self.ax.fill_between(tiempos, velocidades, color="#1f6aa5", alpha=0.2)
        
        self.ax.set_title("", color=text_color, fontsize=10, pad=0)
        self.ax.set_ylabel("Vel", color=text_color, fontsize=8)
        self.ax.set_xlabel("Tiempo", color=text_color, fontsize=8)
        self.fig.tight_layout()
        self.canvas.draw()

        # Reflejo en gráfica flotante auxiliar si está activa
        if hasattr(self, 'top_grafica') and self.top_grafica and self.top_grafica.winfo_exists():
            self.ax_flotante.clear()
            self.fig_flotante.patch.set_facecolor(bg_color)
            self.ax_flotante.set_facecolor(bg_color)
            self.ax_flotante.tick_params(colors=text_color, labelsize=10)
            for spine in self.ax_flotante.spines.values(): spine.set_color(text_color)
            
            self.ax_flotante.plot(tiempos, velocidades, color="#1f6aa5", linewidth=2)
            self.ax_flotante.fill_between(tiempos, velocidades, color="#1f6aa5", alpha=0.2)
            self.ax_flotante.set_title("Perfil de Velocidad Trapezoidal", color=text_color, fontsize=14, pad=10)
            self.ax_flotante.set_ylabel("Velocidad (steps/s)", color=text_color, fontsize=10)
            self.ax_flotante.set_xlabel("Tiempo (s)", color=text_color, fontsize=10)
            self.fig_flotante.tight_layout()
            self.canvas_flotante.draw()

    def _check_scroll(self, event=None):
        """Dispara evaluación diferida del scroll en la consola principal."""
        self.root.after(50, self._eval_scroll)
        
    def _eval_scroll(self):
        """Evalúa si mostrar el botón flotante en la consola base tras scroll manual."""
        y_scroll = self.consola._textbox.yview()[1]
        if y_scroll < 0.98:
            self.btn_scroll_down.place(relx=0.99, rely=0.95, anchor="se")
        else:
            self.btn_scroll_down.place_forget()

    def _check_scroll_flotante(self, event=None):
        """Dispara evaluación diferida del scroll en la consola secundaria."""
        self.root.after(50, self._eval_scroll_flotante)

    def _eval_scroll_flotante(self):
        """Evalúa si mostrar el botón flotante en la consola exterior tras scroll manual."""
        if hasattr(self, 'consola_flotante') and self.consola_flotante.winfo_exists():
            y_scroll = self.consola_flotante._textbox.yview()[1]
            if y_scroll < 0.98:
                self.btn_scroll_flotante.place(relx=0.99, rely=0.95, anchor="se")
            else:
                self.btn_scroll_flotante.place_forget()

    def _scroll_to_bottom(self):
        """Baja el scroll manualmente forzado desde el botón emergente en main."""
        self.btn_scroll_down.place_forget() 
        self.consola.see(tk.END)
        self.root.update_idletasks() 

    def _scroll_to_bottom_flotante(self):
        """Fuerza el scroll hacia el final de forma específica para la consola secundaria."""
        if hasattr(self, 'btn_scroll_flotante'):
            self.btn_scroll_flotante.place_forget()
            
        if hasattr(self, 'consola_flotante'):
            self.consola_flotante.see(tk.END)
        
        self.root.update_idletasks()

    def abrir_consola_flotante(self):
        """Construye y separa la consola principal al exterior para multi-monitor."""
        if hasattr(self, 'top_consola') and self.top_consola and self.top_consola.winfo_exists():
            self.top_consola.lift()
            return
            
        self.top_consola = ctk.CTkToplevel(self.root)
        self.top_consola.title("Consola Detallada de Telemetría")
        self.top_consola.geometry("800x400")
        
        self.top_consola.attributes('-topmost', True)
        
        self.btn_scroll_flotante = ctk.CTkButton(self.top_consola, text="⬇ Ir al final", width=90, height=24, fg_color="#444", hover_color="#555", command=self._scroll_to_bottom_flotante)

        self.consola_flotante = ctk.CTkTextbox(self.top_consola, fg_color="#0c0c0c", text_color="#33ff33", font=ctk.CTkFont(family="Consolas", size=13), wrap="word")
        self.consola_flotante.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Botón de scroll para la consola flotante anclado dentro
        self.btn_scroll_flotante = ctk.CTkButton(self.consola_flotante, text="⬇", width=30, height=30, fg_color="#444", hover_color="#555", corner_radius=6, command=self._scroll_to_bottom_flotante)
        
        # Bindings para chequear scroll manual en la consola auxiliar
        self.consola_flotante._textbox.bind("<MouseWheel>", self._check_scroll_flotante)
        self.consola_flotante._textbox.bind("<B1-Motion>", self._check_scroll_flotante)
        self.consola_flotante._textbox.bind("<ButtonRelease-1>", self._check_scroll_flotante)

        self.consola_flotante.insert("1.0", self.consola.get("1.0", tk.END))
        self.consola_flotante.see(tk.END)
        self.consola_flotante.configure(state='disabled')

    def abrir_grafica_flotante(self):
        """Desacopla el renderizado estático del canvas a una ventana escalable superior."""
        if hasattr(self, 'top_grafica') and self.top_grafica and self.top_grafica.winfo_exists():
            self.top_grafica.lift()
            return
            
        self.top_grafica = ctk.CTkToplevel(self.root)
        self.top_grafica.title("Análisis de Perfil de Velocidad")
        self.top_grafica.geometry("700x450")
        
        self.top_grafica.attributes('-topmost', True)
        
        self.fig_flotante = Figure(figsize=(6, 4), dpi=100)
        self.ax_flotante = self.fig_flotante.add_subplot(111)
        self.canvas_flotante = FigureCanvasTkAgg(self.fig_flotante, master=self.top_grafica)
        self.canvas_flotante.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.actualizar_grafica()

    def cambiar_apariencia(self, nueva_apariencia):
        """Aplica el tema claro u oscuro global a la app CustomTkinter."""
        ctk.set_appearance_mode(nueva_apariencia)
        self.actualizar_grafica() 

    def cambiar_color(self, nuevo_color):
        """Aviso de color primario seleccionado en Config."""
        print(f"[INFO] El color '{nuevo_color}' se aplicará por completo al reiniciar el programa.")

    def toggle_simulador(self):
        """Alterna el bloqueo de puerto para inyectar comandos simulados."""
        if self.var_simulador.get():
            self.combo_puertos.set("SIMULADOR")
            self.combo_puertos.configure(state="disabled")
            print("[INFO] Modo de simulación activado.")
        else:
            self.combo_puertos.configure(state="normal")
            self.combo_puertos.set("")
            if self.motor.conexion == MotorControl.SIMULADOR_ID:
                self.motor.conexion = None
                self.actualizar_led_conexion(False)
            print("[INFO] Modo de simulación desactivado.")

    def actualizar_progreso_ui(self, movs, seg_restantes):
        """Refresca las métricas de UI de contador y temporizador inverso."""
        def _update():
            self.label_movimientos.configure(text=f"Movs: {movs}")
            if seg_restantes > 0:
                h, m, s = int(seg_restantes // 3600), int((seg_restantes % 3600) // 60), int(seg_restantes % 60)
                self.label_reloj.configure(text=f"⌛ {h:02d}:{m:02d}:{s:02d}")
            else:
                self.label_reloj.configure(text="⌛ 00:00:00", text_color="#cc0000")
        self.root.after(0, _update)

    def actualizar_led_conexion(self, conectado):
        """Intercambia el status visual verde/rojo para enchufe USB."""
        def _update():
            if conectado: self.led_conexion.configure(text="🟢 CONECTADO", text_color="#2ecc71")
            else: self.led_conexion.configure(text="🔴 DESCONECTADO", text_color="#cc0000")
        self.root.after(0, _update)

    def actualizar_led_motor(self, estado):
        """Modifica texto descriptivo Leds dependiendo bandera del Thread."""
        def _update():
            if estado == "REPOSO": self.led_motor.configure(text="⚪ MOTOR: REPOSO", text_color="gray60")
            elif estado == "HOMING": self.led_motor.configure(text="🟠 MOTOR: HOMING", text_color="#fd7e14")
            elif estado == "MOVIENDO": self.led_motor.configure(text="🔵 MOTOR: MOVIENDO", text_color="#1f6aa5")
        self.root.after(0, _update)

    def toggle_entries(self):
        """Desactiva dinámicamente cuadros manuales dependiendo del booleano."""
        hay_csv = len(self.motor.rutina_csv) > 0
        
        self.entry_ang.configure(state="disabled" if self.var_rand_ang.get() or hay_csv else "normal")
        self.entry_vel.configure(state="disabled" if self.var_rand_vel.get() or hay_csv else "normal")
        self.entry_acc.configure(state="disabled" if self.var_rand_acc.get() or hay_csv else "normal")
        
        if self.var_link_acc_dec.get() or hay_csv:
            self.check_rand_dec.configure(state="disabled")
            self.entry_dec.configure(state="disabled")
        else:
            self.check_rand_dec.configure(state="normal")
            self.entry_dec.configure(state="disabled" if self.var_rand_dec.get() else "normal")

    # =============================================================================
    # COMANDOS A CAPA DE LÓGICA
    # =============================================================================
    def comando_enviar_kvals(self):
        """Manda configuración de los puentes H integrados L6470 a controlador C++."""
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
        """Trigger de homing UI a Lógica Base con timeout adaptado."""
        if self.motor.entrenando: return
        puerto = self.combo_puertos.get()
        baud = self.entry_baud.get()
        simulador = self.var_simulador.get()
        
        if self.motor.conectar_serial(puerto, baud, simulador, timeout=12.0):
            self.motor.ejecutar_homing()

    def comando_start(self):
        """Recopila datos interfaz en array json y llama al wrapper iniciar subproceso."""
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
        """Solicita detención bandera run=False para pausado asíncrono correcto."""
        self.motor.detener_entrenamiento()
    
    def comando_cargar_csv(self):
        """Abre FileDialog para alimentar listado rutinario externo pregrabado."""
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
                self.label_csv.configure(text=f"{nombre_archivo} ({len(rutina_temp)} movs)", text_color="#2ecc71")
                self.btn_borrar_csv.configure(state="normal")
                self.cb_movimiento()
                print(f"[✔] CSV cargado con éxito: {nombre_archivo}")
            else:
                print("[!] El archivo CSV está vacío o el formato es incorrecto.")
        except Exception as e:
            print(f"[!] Error al leer el CSV: {e}")
        
    def borrar_rutina_csv(self):
        """Elimina archivo de array cache y restaura botones default manuales."""
        self.motor.rutina_csv = []
        self.label_csv.configure(text="Modo: Aleatorio/Fijo", text_color="gray50")
        self.btn_borrar_csv.configure(state="disabled")
        self.cb_movimiento()
        print("[-] Rutina CSV descartada. Volviendo a modo manual.")

    # =============================================================================
    # CONFIGURACIÓN LOCAL Y CIERRE
    # =============================================================================
    def guardar_configuracion(self):
        """Dumpea valores default de los Input Text a un archivo de config externo persistente."""
        config = {
            "puerto": self.combo_puertos.get(), 
            "baud": self.entry_baud.get(), 
            "horas": self.entry_horas.get(), 
            "espera": self.entry_espera.get(),
            "apariencia": self.opcion_apariencia.get(),
            "color_tema": self.opcion_color.get()
        }
        with open(self.archivo_config, 'w') as f: 
            json.dump(config, f)

    def cargar_configuracion(self):
        """Lee el JSON local e inyecta la memoria a los Inputs al abrir el programa."""
        if os.path.exists(self.archivo_config):
            try:
                with open(self.archivo_config, 'r') as f:
                    c = json.load(f)
                    self.combo_puertos.set(c.get("puerto", ""))
                    self.entry_baud.insert(0, c.get("baud", "115200"))
                    self.entry_horas.insert(0, c.get("horas", "0.5"))
                    self.entry_espera.insert(0, c.get("espera", "5.0"))
                    self.opcion_apariencia.set(c.get("apariencia", "Dark"))
                    self.opcion_color.set(c.get("color_tema", "blue"))
            except Exception:
                pass
        self.cb_movimiento()

    def cerrar_aplicacion(self):
        """Ata el cierre de cruz superior a las utilidades seguras de puerto COM y config."""
        self.guardar_configuracion()
        self.motor.cerrar_conexion()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = MotorGUI(root)
    root.mainloop()