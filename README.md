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

### 📡 Procesamiento de Comandos (Parsing)
La comunicación entre el PC (Python) y el Microcontrolador (C) se realiza mediante un protocolo de texto plano. El firmware utiliza la función `sscanf` para decodificar las instrucciones recibidas por el puerto serie.

#### Ubicación del código:
El procesamiento ocurre en el archivo `Core/Src/NRT_Task.c`, dentro del bucle principal de la tarea de tiempo real.

#### Funcionamiento técnico:
Cuando llega una cadena de caracteres, el sistema aplica el siguiente formato de extracción:
```c
// Ejemplo del código en C
sscanf(buffer, "V:%f,A:%f,G:%f", &vel, &acc, &angulo);