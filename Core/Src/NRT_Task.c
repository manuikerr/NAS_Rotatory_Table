/*
 * NRT_Task.c
 *
 * Created on: Mar 29, 2025
 * Author: Angel Jimenez
 */

#include "stm32l4xx_hal.h"
#include "FreeRTOS.h"
#include "Task.h"
#include "L6470_Driver.h"
#include <stdlib.h> // Para conversiones de datos y gestión de tipos estándar
#include <stdio.h>  // Para sscanf(): permite desempaquetar las tramas recibidas por el PC
#include "usbd_cdc_if.h"

// Importamos el puerto serie (UART1)
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

// espera mientras está ocupado
void wait_while_busy() {
    while(dSPIN_Busy_SW()) {
        vTaskDelay(10);
    }
}

// moverse a un ángulo (posición absoluta)
void move_to_ang(float ang){
	dSPIN_Go_To(K_ANG * ang);
	vTaskDelay(2);
	wait_while_busy();
}

// rutina de homing
void homing_routine(void){
	// 1. Aproximación al sensor
	dSPIN_Go_Until(ACTION_RESET, REV, 15000);
	wait_while_busy();

	// 2. Liberación suave del sensor
	dSPIN_Release_SW(ACTION_RESET, FWD);
	wait_while_busy();

	// 3. Movimiento relativo de 90 grados para separarse
	uint32_t pasos_offset = (uint32_t)(K_ANG * 90.0f);
	dSPIN_Move(FWD, pasos_offset);
	wait_while_busy();

	// 4. Establecemos la posición actual como el Cero Lógico (Home)
	dSPIN_Reset_Pos();
}


// estados
typedef enum {
	NRT_STATE_IDLE,
    NRT_STATE_PARSING,
	NRT_STATE_UPDATE,
    NRT_STATE_HOMING,
    NRT_STATE_MOVING,
    NRT_STATE_ERROR
} NRT_State_t;

// Variables globales del puente
char usb_rx_buffer[64];
volatile uint8_t usb_rx_flag = 0;


void NRT_Task(void * parg){

	// --- 1. INICIALIZACIÓN ---
	dSPIN_Init_Sem();
	Init_NRT();
	vTaskDelay(100);

	char tx_buffer[64];
	float vel = 0.0f, acc = 0.0f, dec = 0.0f, angulo = 0.0f;
	int k_hold = 0, k_run = 0, k_acc = 0, k_dec = 0;

	NRT_State_t current_state = NRT_STATE_IDLE;

	// --- 2. BUCLE DE ESPERA DE ÓRDENES ---
	while(1){
		switch(current_state) {
		case NRT_STATE_IDLE:
			// Flag USB activa -> parseamos
			// else -> esperamos
			if (usb_rx_flag == 1) {
				current_state = NRT_STATE_PARSING;
			} else {
				vTaskDelay(10);
			}
			break;

		case NRT_STATE_PARSING:
			// 1. else if comando de entrenamiento -> movemos motor
			if (sscanf((char*)usb_rx_buffer, "V:%f,A:%f,D:%f,G:%f", &vel, &acc, &dec, &angulo) == 4) {
			                current_state = NRT_STATE_MOVING;
			}
			// 2. HOME -> rutina homing
			else if (strncmp((char*)usb_rx_buffer, "HOME", 4) == 0) {
				current_state = NRT_STATE_HOMING;
            }
			// 3. else if k_values -> update
			else if (sscanf((char*)usb_rx_buffer, "K:%d,%d,%d,%d", &k_hold, &k_run, &k_acc, &k_dec) == 4) {
			    current_state = NRT_STATE_UPDATE;
			}
			// 4. else -> ERROR parseo
			else {
                current_state = NRT_STATE_ERROR;
            }
            break;

		case NRT_STATE_UPDATE:

			printf("Actualizando K_Values...");

			// 1. Aplicamos K_Values
			dSPIN_Set_Param(dSPIN_KVAL_HOLD, Kval_Perc_to_Par(k_hold));
			dSPIN_Set_Param(dSPIN_KVAL_RUN,  Kval_Perc_to_Par(k_run));
			dSPIN_Set_Param(dSPIN_KVAL_ACC,  Kval_Perc_to_Par(k_acc));
			dSPIN_Set_Param(dSPIN_KVAL_DEC,  Kval_Perc_to_Par(k_dec));

			// 2. Avisamos de que ha ido bien y oonemos los valores
			snprintf(tx_buffer, sizeof(tx_buffer), "KVAL OK -> HOLD:%d%% RUN:%d%% ACC:%d%% DEC:%d%%\n", k_hold, k_run, k_acc, k_dec);
			CDC_Transmit_FS((uint8_t*)tx_buffer, strlen(tx_buffer));

			// 3. Ponemos flag USB a 0 y actualizamos estado a IDLE
			usb_rx_flag = 0;
			current_state = NRT_STATE_IDLE;
			break;

		case NRT_STATE_HOMING:

			printf("Comenzando rutina de Homing...");

			// 1. hacemos rutina de homing
			homing_routine();

			// 2. Avisamos de que hemos terminado el homing
			snprintf(tx_buffer, sizeof(tx_buffer), "Homing completado\n");
			CDC_Transmit_FS((uint8_t*)tx_buffer, strlen(tx_buffer));

			//3. Ponemos flag USB a 0 y actualizamos estado a IDLE
			usb_rx_flag = 0;
			current_state = NRT_STATE_IDLE;
			break;

		case NRT_STATE_MOVING:
			// 1. Imprime en la consola interna del STM32
			printf("Angulo recibido: %.2f\r\n", angulo);

			// 2. Actualizamos los parámetros del motor "al vuelo"
			dSPIN_Set_Param(dSPIN_MAX_SPEED, MaxSpd_Steps_to_Par(vel));
			dSPIN_Set_Param(dSPIN_ACC, AccDec_Steps_to_Par(acc));
			dSPIN_Set_Param(dSPIN_DEC, AccDec_Steps_to_Par(dec));

			// 3. Movemos la plataforma
			move_to_ang(angulo);

			// 4. Avisamos a Python de que ha ido bien
			snprintf(tx_buffer, sizeof(tx_buffer), "Trama recibida\n");
			CDC_Transmit_FS((uint8_t*)tx_buffer, strlen(tx_buffer));

			// 5. Ponemos flag USB a 0 y actualizamos estado a IDLE
			usb_rx_flag = 0;
			current_state = NRT_STATE_IDLE;
			break;

		case NRT_STATE_ERROR:
			// 1. Imprime en la consola interna del STM32 el error
			printf("Parseo erroneo: %s\r\n", usb_rx_buffer);

			// 2. Avisamos a Python de que ha ido MAL
			snprintf(tx_buffer, sizeof(tx_buffer), "Parseo erroneo\n");
			CDC_Transmit_FS((uint8_t*)tx_buffer, strlen(tx_buffer));

			// 3. Ponemos flag USB a 0 y actualizamos estado a IDLE
			usb_rx_flag = 0;
			current_state = NRT_STATE_IDLE;
			break;
		}
	}
}
