/*
 * NRT_Task.c
 *
 * Created on: Mar 29, 2025
 * Author: Angel Jimenez
 */

#include "stm32l412xx.h"
#include "FreeRTOS.h"
#include "Task.h"
#include "L6470_Driver.h"
#include <stdlib.h> // Para conversiones de datos y gestión de tipos estándar
#include <string.h> // Para memset(): vital para limpiar el buffer UART y evitar basura en los comandos
#include <stdio.h>  // Para sscanf(): permite desempaquetar la trama V,A,G recibida del PC

// Importamos el puerto serie (UART1) que ya está inicializado en usart.c o main.c
extern UART_HandleTypeDef huart1;

// Factor de conversión (Ajusta este valor según la reducción de tu motor)
#define K_ANG 768000.0f/360.0f

void Init_NRT(){
	dSPIN_RegsStruct_TypeDef dSPIN_RegsStruct;

	dSPIN_Hard_HiZ();
	dSPIN_Reset_Device();
	dSPIN_Regs_Struct_Reset(&dSPIN_RegsStruct);

	/* Acceleration & Deceleration */
	dSPIN_RegsStruct.ACC 		= AccDec_Steps_to_Par(8000);
	dSPIN_RegsStruct.DEC 		= AccDec_Steps_to_Par(8000);
	dSPIN_RegsStruct.MAX_SPEED 	= MaxSpd_Steps_to_Par(780);
	dSPIN_RegsStruct.FS_SPD 	= FSSpd_Steps_to_Par(780);
	dSPIN_RegsStruct.MIN_SPEED 	= dSPIN_CONF_PARAM_LSPD_BIT|MinSpd_Steps_to_Par(0);

	/* KVAL (Voltajes de fase) - Ajustar si el motor no tiene fuerza o se calienta */
	dSPIN_RegsStruct.KVAL_HOLD 	= Kval_Perc_to_Par(10);
	dSPIN_RegsStruct.KVAL_RUN 	= Kval_Perc_to_Par(30);
	dSPIN_RegsStruct.KVAL_ACC 	= Kval_Perc_to_Par(30);
	dSPIN_RegsStruct.KVAL_DEC 	= Kval_Perc_to_Par(30);

	dSPIN_RegsStruct.K_THERM 	= KTherm_to_Par(dSPIN_CONF_PARAM_K_THERM);
	dSPIN_RegsStruct.INT_SPD 	= IntSpd_Steps_to_Par(dSPIN_CONF_PARAM_INT_SPD);
	dSPIN_RegsStruct.ST_SLP 	= BEMF_Slope_Perc_to_Par(dSPIN_CONF_PARAM_ST_SLP);
	dSPIN_RegsStruct.FN_SLP_ACC = BEMF_Slope_Perc_to_Par(dSPIN_CONF_PARAM_FN_SLP_ACC);
	dSPIN_RegsStruct.FN_SLP_DEC = BEMF_Slope_Perc_to_Par(dSPIN_CONF_PARAM_FN_SLP_DEC);
	dSPIN_RegsStruct.STALL_TH 	= StallTh_to_Par(dSPIN_CONF_PARAM_STALL_TH);

	/* CONFIGURACIÓN CON MODO HARD_STOP */
	dSPIN_RegsStruct.CONFIG 	= (uint16_t)dSPIN_CONF_PARAM_CLOCK_SETTING |
	                                      (uint16_t)dSPIN_CONF_PARAM_SW_MODE	   |
	                                      (uint16_t)dSPIN_CONF_PARAM_VS_COMP       |
	                                      (uint16_t)dSPIN_CONF_PARAM_OC_SD         |
	                                      (uint16_t)dSPIN_CONF_PARAM_SR	           |
	                                      (uint16_t)dSPIN_CONF_PARAM_PWM_DIV       |
	                                      (uint16_t)dSPIN_CONF_PARAM_PWM_MUL;

	dSPIN_RegsStruct.OCD_TH 	= dSPIN_CONF_PARAM_OCD_TH;
	dSPIN_RegsStruct.ALARM_EN 	= dSPIN_CONF_PARAM_ALARM_EN;
	dSPIN_RegsStruct.STEP_MODE 	= (uint8_t)dSPIN_CONF_PARAM_SYNC_MODE |
	                                      (uint8_t)dSPIN_CONF_PARAM_STEP_MODE;

	dSPIN_Registers_Set(&dSPIN_RegsStruct);
}

void wait_while_busy() {
    while(dSPIN_Busy_SW()) {
        vTaskDelay(10);
    }
}

void move_to_ang(float ang){
	dSPIN_Go_To(K_ANG * ang);
	vTaskDelay(2);
	wait_while_busy();
}

void NRT_Task(void * parg){

	dSPIN_Init_Sem();
	Init_NRT();
	vTaskDelay(100);

	// --- 1. RUTINA DE HOMING (Búsqueda del Cero Inicial) ---
	dSPIN_Go_Until(dSPIN_ACTION_RESET, dSPIN_DIR_REV, 15000);
	wait_while_busy();

	dSPIN_Release_SW(dSPIN_ACTION_RESET, dSPIN_DIR_FWD);
	wait_while_busy();

	// --- 2. PREPARACIÓN PARA RECIBIR COMANDOS POR SERIAL ---
		char rx_buffer[64];
		memset(rx_buffer, 0, sizeof(rx_buffer));
		uint8_t rx_index = 0;
		uint8_t rx_data = 0;

		// --- 3. BUCLE DE ESPERA DE ÓRDENES ---
		while(1){
			// Leemos el puerto serie (espera máxima 10ms por vuelta)
			if (HAL_UART_Receive(&huart1, &rx_data, 1, 10) == HAL_OK) {

				// Si el usuario pulsa 'Enter' (salto de línea)
				if (rx_data == '\n' || rx_data == '\r') {
					if (rx_index > 0) {

						float vel = 0.0f, acc = 0.0f, angulo = 0.0f;

						// Desmenuzamos el texto: V:vel,A:acc,G:angulo
						if (sscanf(rx_buffer, "V:%f,A:%f,G:%f", &vel, &acc, &angulo) == 3) {

							// 1. Actualizamos los parámetros del motor "al vuelo"
							dSPIN_Set_Param(dSPIN_MAX_SPEED, MaxSpd_Steps_to_Par(vel));
							dSPIN_Set_Param(dSPIN_ACC, AccDec_Steps_to_Par(acc));
							dSPIN_Set_Param(dSPIN_DEC, AccDec_Steps_to_Par(acc));

							// 2. Mover la plataforma
							move_to_ang(angulo);
						}

						// 3. Limpiar buffer para la próxima orden
						memset(rx_buffer, 0, sizeof(rx_buffer));
						rx_index = 0;
					}
				}
				// Si no es un salto de línea, seguimos guardando caracteres
				else if (rx_index < 63) {
					rx_buffer[rx_index] = (char)rx_data;
					rx_index++;
				}
			} else {
				// Si no ha llegado nada por serial, cedemos el control a FreeRTOS
				vTaskDelay(10);
			}
		}
}
