\# NAS Rotatory Table



Este proyecto implementa un sistema de control de alta precisión para una mesa giratoria utilizada en el entrenamiento y validación de dispositivos auditivos. El sistema utiliza un microcontrolador \*\*STM32L412\*\* y el driver de motor paso a paso \*\*L6470 (dSPIN)\*\*.



\## 🚀 Características

\- \*\*Control dinámico:\*\* Ajuste de velocidad, aceleración y ángulo "al vuelo" mediante comandos seriales.

\- \*\*Modo Silencioso:\*\* Configurado a 1/128 micropasos para minimizar vibraciones y ruido acústico.

\- \*\*Homing Automático:\*\* Rutina de calibración inicial mediante sensor de fin de carrera.

\- \*\*Multitarea:\*\* Basado en \*\*FreeRTOS\*\* para una gestión eficiente de los recursos.



\## 📂 Estructura del Proyecto

\- `/Core`: Código fuente del firmware en C.

\- `L6470\_Driver.c/h`: Librería de bajo nivel para la comunicación SPI con el driver.

\- `NRT\_Task.c`: Lógica de la tarea principal y procesamiento de comandos.

\- `script\_mesa.py`: Script de Python para el control automático y aleatorio desde el PC.

