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
    """Construye la ruta absoluta para recursos estáticos dentro de assets/img."""
    return os.path.join(RUTA_BASE, "assets", "img", nombre_archivo)

class ECHOSplash:
    def __init__(self, root):
        """Configura el Splash Screen usando un Canvas para garantizar transparencias alfa reales."""
        self.root = root
        self.cargando = True 
        
        self.root.overrideredirect(True) 
        width, height = 600, 600
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        fondo_gris = "#d3d3d3" 
        self.root.configure(bg=fondo_gris)

        self.canvas = tk.Canvas(self.root, width=width, height=height, bg=fondo_gris, highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill="both", expand=True)

        try:
            ruta_fondo = obtener_ruta_recurso("pantalla_carga.png")
            img_bg = Image.open(ruta_fondo).convert("RGBA")
            img_bg = img_bg.resize((width, height), Image.LANCZOS)
            self.img_fondo = ImageTk.PhotoImage(img_bg)
            self.canvas.create_image(0, 0, image=self.img_fondo, anchor="nw")
        except Exception:
            pass

        try:
            ruta_engranaje = obtener_ruta_recurso("engranaje.png")
            self.img_engranaje_original = Image.open(ruta_engranaje).convert("RGBA")
            self.img_engranaje_original = self.img_engranaje_original.resize((40, 40), Image.LANCZOS)
            
            self.engranaje_x = width // 2
            self.engranaje_y = height - 100
            
            self.canvas_engranaje_id = self.canvas.create_image(self.engranaje_x, self.engranaje_y, anchor="center")
        except Exception:
            self.img_engranaje_original = None

        self.canvas.create_text(20, height - 30, text="v2.0.0", fill="#666666", font=("Arial", 12, "bold"), anchor="w")
        
        self.angulo_engranaje = 0
        self.animacion_id = None
        
        self.animar_carga()
        self.iniciar_carga_en_segundo_plano()

    def animar_carga(self):
        """Gestiona la rotación matemática del engranaje redibujándolo sobre el Canvas."""
        if not self.cargando:
            return

        if hasattr(self, 'img_engranaje_original') and self.img_engranaje_original:
            try:
                self.angulo_engranaje = (self.angulo_engranaje - 5) % 360
                
                img_rotada = self.img_engranaje_original.rotate(self.angulo_engranaje, resample=Image.BICUBIC, expand=False, fillcolor=(0, 0, 0, 0))
                
                self.tk_engranaje = ImageTk.PhotoImage(img_rotada)
                self.canvas.itemconfig(self.canvas_engranaje_id, image=self.tk_engranaje)
                
            except Exception:
                pass
        
        if self.cargando:
            self.animacion_id = self.root.after(30, self.animar_carga)

    def iniciar_carga_en_segundo_plano(self):
        """Lanza un hilo dedicado para importar las librerías pesadas sin bloquear el Main Thread."""
        hilo_carga = threading.Thread(target=self.importar_dependencias_pesadas, daemon=True)
        hilo_carga.start()
        self.comprobar_estado_carga(hilo_carga)

    def importar_dependencias_pesadas(self):
        """Carga en la memoria RAM los módulos críticos del sistema."""
        global interfaz_motor
        import customtkinter as ctk
        import interfaz_motor 
        import matplotlib.pyplot as plt 

    def comprobar_estado_carga(self, hilo):
        """Monitorea el estado del hilo de carga para destruir el Splash al finalizar."""
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
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root_splash = tk.Tk()
    app_splash = ECHOSplash(root_splash)
    root_splash.mainloop() 
    
    import customtkinter as ctk
    from interfaz_motor import MotorGUI 
    
    root_app = ctk.CTk()
    app_principal = MotorGUI(root_app)
    root_app.mainloop()