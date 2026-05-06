# NAS Rotatory Table

Este proyecto implementa un sistema de control de alta precisión para una mesa giratoria utilizada en el entrenamiento y validación de dispositivos auditivos (ecolocalización). El sistema utiliza un microcontrolador **STM32L412** y el driver de motor paso a paso **L6470**.

## 📂 Estructura del Proyecto

- `/Core`: Código fuente del firmware en C para el STM32.
  - `L6470_Driver.c`: Librería de bajo nivel para la comunicación SPI con el driver.
  - `NRT_Task.c`: Tarea principal de FreeRTOS, bucle de control USB CDC, parsing y movimiento.
  - `gpio.c`: Inicialización segura de pines y periféricos (NSS, LEDs).
- `/GUI_Motor`: Entorno de desarrollo de la interfaz gráfica de control desde el PC.
  - `interfaz_motor.py`: Código fuente en Python con hilos paralelos de transmisión y logging.
  - Recursos gráficos (`us.png`, `icofinal.ico`).

> **📥 Descarga del Software:** El ejecutable precompilado de la interfaz para Windows (`E.C.H.O. Platform.exe`) se encuentra disponible en la sección **[Releases](https://github.com/manuikerr/NAS_Rotatory_Table/releases)e este repositorio dentro de un archivo empaquetado junto a sus dependencias.

---

# 📝 Registro de Modificaciones y Evolución del Proyecto

Este apartado detalla la transición desde la plantilla base inicial hacia el sistema de automatización dinámico y visual actual.

## 🏗️ 1. Infraestructura Base 
Se ha mantenido la arquitectura original, que proporciona la estabilidad necesaria para el tiempo real:
* **Arquitectura de Tiempo Real:** Configuración de **FreeRTOS** y creación de la tarea `NRT_Task` para el control del motor.
* **Comunicación SPI de Alta Eficiencia:** Implementación de **Semáforos Binarios** (`spiSem`) para evitar el bloqueo del procesador mediante transferencias por interrupción (`HAL_SPI_TransmitReceive_IT`).
* **Cálculo de Resolución:** Definición de la constante `K_ANG` para la conversión de grados a pasos del motor.

## 🚀 2. Mejoras de Hardware y Firmware (STM32)
El firmware se ha optimizado para transformarlo en un sistema modular, seguro y reactivo mediante los siguientes hitos de desarrollo:

### 🔌 Configuración del Periférico USB CDC
* **Puerto Virtual COM:** Se configuró el periférico USB del STM32 en modo **CDC (Communications Device Class)**. Esto permite recibir y transmitir datos simulando un puerto serie nativo directo al PC, procesando instrucciones de manera síncrona mediante un buffer de recepción de **64 bytes** (`usb_rx_buffer`).

### ⚙️ Optimización Eléctrica de Pines (`gpio.c`)
* **Estado Inicial Seguro:** Se modificó la inicialización de los pines para garantizar la estabilidad eléctrica desde el arranque:
    * **Pin NSS en ALTO (`GPIO_PIN_SET`):** Se fuerza el pin de selección de esclavo SPI a nivel alto inmediatamente. Esto mantiene al driver **L6470** en reposo, evitando que interprete ruido electrónico como comandos falsos durante la fase de inicio del microcontrolador.
    * **LEDs en BAJO (`GPIO_PIN_RESET`):** Los indicadores visuales comienzan apagados para una gestión de estados limpia.

### 🧠 Máquina de Estados Estructurada (`NRT_Task.c`)
* **Control de Ciclo de Vida:** El bucle infinito de la tarea `NRT_Task` actúa como una **Máquina de Estados reactiva** coordinada por hilos de FreeRTOS. El sistema permanece bloqueado cediendo tiempo de CPU (`vTaskDelay(10)`) hasta que la interrupción del USB activa la bandera `usb_rx_flag == 1`, momento en el que conmuta de forma segura entre la decodificación de tramas, llamadas al hardware o rutinas críticas de posición sin bloquear los hilos paralelos.

### 🛠️ Comandos Dinámicos y Calibración de Home
* **Comando Explícito de HOME:** Se desarrolló una instrucción de texto específica (`"HOME"`). Al ser leída por `strncmp`, conmuta inmediatamente a la función `homing_routine()`, forzando al motor a buscar su origen físico 0° y notificando su fin mediante el buffer de transmisión (`"Homing completado\n"`).
* **Parsing Avanzado con Soporte Float:** El firmware procesa tramas complejas, admitiendo la configuración simultánea de **Velocidad, Aceleración, Desaceleración y Ángulo**. Se habilitó el soporte de tipos *float* en los *Linker Flags* del proyecto (`-u _scanf_float`) para el correcto funcionamiento de `sscanf` sobre el formato `"V:%f,A:%f,D:%f,G:%f"`.
* **Control "al vuelo":** Llamadas dinámicas a `dSPIN_Set_Param` usando funciones de conversión de parámetros de movimiento de pasos a registros (`MaxSpd_Steps_to_Par`, `AccDec_Steps_to_Par`), modificando las rampas físicas en caliente antes de ejecutar la trayectoria final `move_to_ang(angulo)`.

### 🔄 Protocolo de Comunicación y Handshake Bidireccional
Se ha diseñado un canal de comunicación síncrono entre la placa y el ordenador con confirmación de eventos (*handshake*):
* **Lado STM32 (Consola Interna):** El microcontrolador decodifica las tramas e imprime explícitamente en su consola serie el ángulo objetivo calculado (`printf("Angulo: %.2f\r\n")`) o la traza exacta de fallo en caso de datos corruptos (`printf("Parseo erroneo: %s\r\n")`).
* **Lado Script Python (Handshake de Control):** Tras enviar una instrucción, el script de Python bloquea temporalmente el puerto esperando la respuesta síncrona del STM32 (`self.conexion.readline()`):
    * Si el parseo es correcto, el STM32 devuelve el token **`Angulo recibido`**, permitiendo reflejar el éxito en la telemetría del PC.
    * Si la trama falla, la placa devuelve el token **`Parseo erroneo`**, alertando a la interfaz de Python para notificar la incidencia y denegar acciones inseguras en el hardware.

## 🖥️ 3. E.C.H.O. Platform - Interfaz de Control del motor (`interfaz_mesa.py`)
Sustitución completa del script de automatización antiguo por un entorno gráfico e interactivo multihilo bajo el ecosistema **E.C.H.O. Platform**.

* **UI para Script Python (GUI_Motor):** Panel visual desarrollado con `tkinter` y empaquetado en un ejecutable independiente de Windows. Implementa redirección completa de la salida estándar `sys.stdout` a un widget de texto en tiempo real (`ConsoleRedirector`) actuando como consola de telemetría integrada.
* **Control Multihilo Síncrono:** La rutina de entrenamiento se ejecuta en un hilo secundario independiente (`threading.Thread`) con opción de parada segura (`self.entrenando = False`), evitando la congelación de la interfaz gráfica durante los retardos de envío y las lecturas por puerto serie.
* **Persistencia de Datos (Smart Config):** Carga y volcado automático de parámetros configurados (puertos COM detectados dinámicamente, Baud Rate, tiempos de espera, banderas de aleatoriedad y valores fijos) mediante un archivo local `config.json` al abrir y cerrar la aplicación.
* **Sistema de Telemetría (Logging):** Registro automatizado en archivos de texto dentro de una carpeta local `/logs`, guardando marcas de tiempo de Windows, estados de respuesta devueltos por el firmware del STM32 y los parámetros exactos calculados (de forma aleatoria o fija) para la posterior auditoría de los ensayos de ecolocalización.