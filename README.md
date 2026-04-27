# NAS Rotatory Table

Este proyecto implementa un sistema de control de alta precisión para una mesa giratoria utilizada en el entrenamiento y validación de dispositivos auditivos. El sistema utiliza un microcontrolador **STM32L412** y el driver de motor paso a paso **L6470**.



## 🚀 Características

- **Control dinámico:** Ajuste de velocidad, aceleración y ángulo "al vuelo" mediante comandos seriales.

- **Modo Silencioso:** Configurado a 1/128 micropasos para minimizar vibraciones y ruido acústico.

- **Homing Automático:** Rutina de calibración inicial mediante sensor de fin de carrera.

- **Multitarea:** Basado en **FreeRTOS** para una gestión eficiente de los recursos.



## 📂 Estructura del Proyecto

- `/Core`: Código fuente del firmware en C.

- `L6470_Driver.c`: Librería de bajo nivel para la comunicación SPI con el driver.

- `NRT_Task.c`: Lógica de la tarea principal y procesamiento de comandos.

- `script_mesa.py`: Script de Python para el control automático y aleatorio desde el PC.



# 📝 Registro de Modificaciones y Evolución del Proyecto

Este apartado detalla la transición desde la plantilla base proporcionada por el docente hacia el sistema de automatización dinámico actual.

## 🏗️ 1. Infraestructura Base (Plantilla del Docente)
Se ha mantenido la arquitectura profesional original, que proporciona la estabilidad necesaria para el tiempo real:

* **Arquitectura de Tiempo Real:** Configuración de **FreeRTOS** y creación de la tarea `NRT_Task` para el control del motor.
* **Comunicación SPI de Alta Eficiencia:** * Implementación de **Semáforos Binarios** (`spiSem`) para evitar el bloqueo del procesador.
    * Uso de transferencias por interrupción (`HAL_SPI_TransmitReceive_IT`) en el driver `L6470_Driver.c`.
* **Cálculo de Resolución:** Definición de la constante `K_ANG` para la conversión de grados a pasos del motor.


## 🚀 2. Adiciones y Mejoras Personales del Alumno Interno
He transformado la base secuencial en una herramienta de laboratorio interactiva y automatizada:

### 📥 Integración de Comunicaciones Dinámicas (`NRT_Task.c`)
* **Protocolo de Comandos Propietario:** Se eliminó el bucle fijo para implementar un sistema de escucha activa por UART.
* **Implementación de Parsing con `sscanf`:** Se añadió la lógica necesaria para "desmenuzar" tramas complejas. Ahora el sistema puede recibir **Velocidad, Aceleración y Ángulo** en un solo comando (`V:f,A:f,G:f`).
* **Control "al vuelo" del L6470:** Se añadieron llamadas dinámicas a `dSPIN_Set_Param`, permitiendo que el motor cambie su comportamiento físico (aceleración y velocidad máxima) sin necesidad de reiniciar el firmware.
* **Gestión de Memoria:** Buffer de recepción de **64 bytes** para soportar instrucciones largas desde el PC.


> **💡 Nota Técnica:** Para asegurar que el `sscanf` funcione correctamente en el STM32, se ha habilitado el soporte de **float** en los *Linker Flags* del proyecto (`-u _scanf_float`).



### 🐍 Automatización Externa (`script_mesa.py`)
* **Desarrollo Íntegro del Controlador Python:** Creación de un script externo para gestionar el entrenamiento del dispositivo.
* **Algoritmo de Aleatoriedad:** Implementación de trayectorias variables para simular escenarios de uso real.
* **Sistema de Telemetría (Logging):** Generación automática de informes en archivos `.txt` con marcas de tiempo y parámetros de cada movimiento.