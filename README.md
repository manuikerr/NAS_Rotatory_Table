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



## 📂 Registro de Modificaciones por Archivo

### `Core/Src/NRT_Task.c`
Este archivo es íntegramente personalizado y contiene la lógica de control de la mesa:
* **Gestión de Memoria:** Se aumentó el tamaño de `rx_buffer` a 64 bytes para permitir la recepción de tramas complejas de comandos.
* **Procesamiento de Comandos:** Sustitución de `atof()` por `sscanf()` con soporte para punto flotante, permitiendo extraer Velocidad, Aceleración y Ángulo en una sola cadena (`V:%f,A:%f,G:%f`).
* **Control del Driver L6470:** Implementación de llamadas dinámicas a `dSPIN_Set_Param` para actualizar los registros de `MAX_SPEED`, `ACC` y `DEC` antes de ejecutar cada movimiento.
* **Rutina de Homing:** Adición de una secuencia de arranque que utiliza el comando `dSPIN_Go_Until` para buscar el sensor de referencia antes de aceptar órdenes del PC.

### `Core/Src/L6470_Driver.c`
Se han añadido funciones para integrar el driver con el sistema operativo de tiempo real:
* **Sincronización:** Implementación de un **Semáforo Binario** (`spiSem`) para gestionar la comunicación SPI de forma no bloqueante dentro de **FreeRTOS**.
* **Interrupciones:** Adición de la función `HAL_SPI_TxRxCpltCallback` para liberar el semáforo una vez que la transferencia de datos por hardware ha finalizado.
* **Configuración Silenciosa:** Ajuste del registro `STEP_MODE` para forzar el uso de **1/128 micropasos**, reduciendo el ruido acústico durante los tests auditivos.

### `Core/Src/main.c`
Modificaciones en el flujo de arranque del sistema:
* **Arquitectura OS:** Se eliminó la lógica del bucle principal `while(1)` original para delegar el control a `osKernelStart()`.
* **Reloj del Sistema:** Configuración específica del oscilador MSI y el PLL para alcanzar la frecuencia necesaria para la comunicación USB y SPI estable.

### `script_mesa.py` (Script de Python)
Archivo creado desde cero para la automatización externa:
* **Protocolo Serial:** Implementación del envío de tramas codificadas en UTF-8 compatibles con el `sscanf` del firmware.
* **Aleatoriedad:** Lógica de generación de trayectorias con parámetros de movimiento (`random.uniform`) para simular condiciones reales de uso.
* **Data Logging:** Sistema de registro automático que guarda cada movimiento con su marca de tiempo en un archivo `.txt`.



> **💡 Nota Técnica:** Para asegurar que el `sscanf` funcione correctamente en el STM32, se ha habilitado el soporte de **float** en los *Linker Flags* del proyecto (`-u _scanf_float`).



### 📡 Procesamiento de Comandos (Parsing)
La comunicación entre el PC (Python) y el Microcontrolador (C) se realiza mediante un protocolo de texto plano. El firmware utiliza la función `sscanf` para decodificar las instrucciones recibidas por el puerto serie.

#### Ubicación del código:
El procesamiento ocurre en el archivo `Core/Src/NRT_Task.c`, dentro del bucle principal de la tarea de tiempo real.

#### Funcionamiento técnico:
Cuando llega una cadena de caracteres, el sistema aplica el siguiente formato de extracción:
```c
// Ejemplo del código en C
sscanf(buffer, "V:%f,A:%f,G:%f", &vel, &acc, &angulo);