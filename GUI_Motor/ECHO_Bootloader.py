import tkinter as tk
from PIL import Image, ImageTk
import threading
import sys
import os

# --- GESTIÓN DE RUTAS DINÁMICAS ---
if hasattr(sys, '_MEIPASS'):
    RUTA_BASE = sys._MEIPASS
else:
    RUTA_BASE = os.path.dirname(os.path.abspath(__file__))

def obtener_ruta_recurso(nombre_archivo):
    """
    Construye la ruta absoluta para recursos estáticos.
    Busca los archivos dentro de la subcarpeta centralizada assets/img.
    """
    return os.path.join(RUTA_BASE, "assets", "img", nombre_archivo)

class ECHOSplash:
    def __init__(self, root):
        """
        Configura la interfaz del Splash Screen: ventana sin bordes,
        centrado en pantalla y carga de elementos visuales iniciales.
        """
        self.root = root
        self.cargando = True # Bandera de control para procesos asíncronos
        
        self.root.overrideredirect(True) 
        width, height = 600, 600
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        fondo_gris = "#d3d3d3" 
        self.root.configure(bg=fondo_gris)

        try:
            ruta_fondo = obtener_ruta_recurso("pantalla_carga.png")
            img_bg = Image.open(ruta_fondo)
            img_bg = img_bg.resize((width, height), Image.LANCZOS)
            self.img_fondo = ImageTk.PhotoImage(img_bg)
            self.lbl_fondo = tk.Label(self.root, image=self.img_fondo, borderwidth=0)
            self.lbl_fondo.place(x=0, y=0)
        except Exception:
            pass

        try:
            ruta_engranaje = obtener_ruta_recurso("engranaje.png")
            self.img_engranaje_original = Image.open(ruta_engranaje).convert("RGBA")
            self.img_engranaje_original = self.img_engranaje_original.resize((40, 40), Image.LANCZOS)
            self.tk_engranaje = ImageTk.PhotoImage(self.img_engranaje_original)
            self.lbl_engranaje = tk.Label(self.root, image=self.tk_engranaje, bg=fondo_gris, borderwidth=0)
            self.lbl_engranaje.place(x=width//2 - 20, y=height - 120) 
        except Exception:
            self.img_engranaje_original = None

        # Etiqueta de versión del software
        self.lbl_version = tk.Label(self.root, text="v2.0.0", bg=fondo_gris, fg="#666666", font=("Arial", 12, "bold"))
        self.lbl_version.place(x=20, y=height - 40)
        
        self.angulo_engranaje = 0
        self.animacion_id = None
        
        self.animar_carga()
        self.iniciar_carga_en_segundo_plano()

    def animar_carga(self):
        """
        Gestiona la rotación del engranaje mediante recursión controlada por .after().
        Aplica rotación a la imagen original para evitar la degradación por rotaciones sucesivas.
        """
        if not self.cargando:
            return

        if hasattr(self, 'img_engranaje_original') and self.img_engranaje_original:
            try:
                self.angulo_engranaje = (self.angulo_engranaje - 5) % 360
                img_rotada = self.img_engranaje_original.rotate(self.angulo_engranaje, resample=Image.BICUBIC)
                self.tk_engranaje = ImageTk.PhotoImage(img_rotada)
                self.lbl_engranaje.config(image=self.tk_engranaje)
            except Exception:
                pass
        
        if self.cargando:
            self.animacion_id = self.root.after(30, self.animar_carga)

    def iniciar_carga_en_segundo_plano(self):
        """
        Lanza un hilo dedicado (Daemon) para importar las librerías pesadas sin
        bloquear el refresco visual de la ventana principal (Main Thread).
        """
        hilo_carga = threading.Thread(target=self.importar_dependencias_pesadas, daemon=True)
        hilo_carga.start()
        self.comprobar_estado_carga(hilo_carga)

    def importar_dependencias_pesadas(self):
        """
        Carga en la memoria RAM los módulos críticos del sistema.
        Al ser imports globales, ya estarán disponibles para interfaz_motor.
        """
        global interfaz_motor, ctk
        import customtkinter as ctk
        import interfaz_motor 
        import matplotlib.pyplot as plt 

    def comprobar_estado_carga(self, hilo):
        """
        Monitorea el estado del hilo de carga. Cuando finaliza, detiene la animación
        y destruye el Splash para dar paso a la aplicación principal.
        """
        if hilo.is_alive():
            self.root.after(100, lambda: self.comprobar_estado_carga(hilo))
        else:
            self.cargando = False
            if self.animacion_id is not None:
                self.root.after_cancel(self.animacion_id)
            self.root.destroy()

# --- BLOQUE DE EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    import ctypes
    try:
        # Configuración de Windows para que la GUI sea nítida en pantallas HiDPI
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # FASE 1: Ejecución del Splash Screen
    root_splash = tk.Tk()
    app_splash = ECHOSplash(root_splash)
    root_splash.mainloop() 
    
    # FASE 2: Una vez cerrado el Splash, se inicia la Interfaz Principal
    import customtkinter as ctk
    from interfaz_motor import MotorGUI 
    
    root_app = ctk.CTk()
    app_principal = MotorGUI(root_app)
    root_app.mainloop()