/*
 * L6470_Driver.h
 *
 *  Created on: 28 mar. 2020
 *      Author: Angel Jimenez
 */

#ifndef L6470_DRIVER_H_
#define L6470_DRIVER_H_

/* Exported constants --------------------------------------------------------*/

  /****************************************************************************/
  /***************** DSPIN chip type ******************************************/
  /****************************************************************************/
  #define L6470 (1)

	/* Register : ACC */
        /* Acceleration rate in step/s2, range 14.55 to 59590 steps/s2 */
    #define dSPIN_CONF_PARAM_ACC (1000)

	/* Register : DEC */
        /* Deceleration rate in step/s2, range 14.55 to 59590 steps/s2 */
    #define dSPIN_CONF_PARAM_DEC (800)

	/* Register : MAX_SPEED */
        /* Maximum speed in step/s, range 15.25 to 15610 steps/s */
    #define dSPIN_CONF_PARAM_MAX_SPEED (600)

	/* Register : MIN_SPEED */
	/* Minimum speed in step/s, range 0 to 976.3 steps/s */
    #define dSPIN_CONF_PARAM_MIN_SPEED (0)

	/* Register : FS_SPD */
        /* Full step speed in step/s, range 7.63 to 15625 steps/s */
    #define dSPIN_CONF_PARAM_FS_SPD (600)

  /************************ Phase Current Control *****************************/

        /* Register : KVAL_HOLD */
	/* Hold duty cycle (torque) in %, range 0 to 99.6% */
    #define dSPIN_CONF_PARAM_KVAL_HOLD (16.02)

	/* Register : KVAL_RUN */
	/* Run duty cycle (torque) in %, range 0 to 99.6% */
    #define dSPIN_CONF_PARAM_KVAL_RUN (16.02)

	/* Register : KVAL_ACC */
        /* Acceleration duty cycle (torque) in %, range 0 to 99.6% */
    #define dSPIN_CONF_PARAM_KVAL_ACC (16.02)

	/* Register : KVAL_DEC */
	/* Deceleration duty cycle (torque) in %, range 0 to 99.6% */
    #define dSPIN_CONF_PARAM_KVAL_DEC (16.02)

	/* Register : CONFIG - field : EN_VSCOMP */
	/* Motor Supply Voltage Compensation enabling , enum dSPIN_CONFIG_EN_VSCOMP_TypeDef */
    #define dSPIN_CONF_PARAM_VS_COMP (dSPIN_CONFIG_VS_COMP_DISABLE)

	/* Register : MIN_SPEED - field : LSPD_OPT */
	/* Low speed optimization bit, enum dSPIN_LSPD_OPT_TypeDef */
    #define dSPIN_CONF_PARAM_LSPD_BIT (dSPIN_LSPD_OPT_OFF)

	/* Register : K_THERM */
	/* Thermal compensation param, range 1 to 1.46875 */
    #define dSPIN_CONF_PARAM_K_THERM (1)

	/* Register : INT_SPEED */
	/* Intersect speed settings for BEMF compensation in steps/s, range 0 to 3906 steps/s */
    #define dSPIN_CONF_PARAM_INT_SPD (61.512)

	/* Register : ST_SLP */
	/* BEMF start slope settings for BEMF compensation in % step/s, range 0 to 0.4% s/step */
    #define dSPIN_CONF_PARAM_ST_SLP (0.03815)

	/* Register : FN_SLP_ACC */
	/* BEMF final acc slope settings for BEMF compensation in % step/s, range 0 to 0.4% s/step  */
    #define dSPIN_CONF_PARAM_FN_SLP_ACC (0.06256)

	/* Register : FN_SLP_DEC */
	/* BEMF final dec slope settings for BEMF compensation in % step/s, range 0 to 0.4% s/step */
    #define dSPIN_CONF_PARAM_FN_SLP_DEC (0.06256)

	/* Register : CONFIG - field : F_PWM_INT */
	/* PWM Frequency Integer division, enum dSPIN_CONFIG_F_PWM_INT_TypeDef */
    #define dSPIN_CONF_PARAM_PWM_DIV (dSPIN_CONFIG_PWM_DIV_1)

	/* Register : CONFIG - field : F_PWM_DEC */
	/* PWM Frequency Integer Multiplier, enum dSPIN_CONFIG_F_PWM_INT_TypeDef */
    #define dSPIN_CONF_PARAM_PWM_MUL (dSPIN_CONFIG_PWM_MUL_2)

  /******************************* Others *************************************/
	/* Register : OCD_TH */
        /* Overcurrent threshold settings via enum dSPIN_OCD_TH_TypeDef */
    #define dSPIN_CONF_PARAM_OCD_TH (dSPIN_OCD_TH_3375mA)

	/* Register : STALL_TH */
	/* Stall threshold settings in mA, range 31.25mA to 4000mA */
    #define dSPIN_CONF_PARAM_STALL_TH (2031.25)

	/* Register : ALARM_EN */
	/* Alarm settings via bitmap enum dSPIN_ALARM_EN_TypeDef */
    #define dSPIN_CONF_PARAM_ALARM_EN (dSPIN_ALARM_EN_OVERCURRENT | dSPIN_ALARM_EN_THERMAL_SHUTDOWN | dSPIN_ALARM_EN_THERMAL_WARNING | dSPIN_ALARM_EN_UNDER_VOLTAGE | dSPIN_ALARM_EN_STALL_DET_A | dSPIN_ALARM_EN_STALL_DET_B  | dSPIN_ALARM_EN_WRONG_NPERF_CMD | dSPIN_ALARM_EN_SW_TURN_ON)

	/* Register : STEP_MODE - field : STEP_MODE */
        /* Step mode settings via enum dSPIN_STEP_SEL_TypeDef */
    #define dSPIN_CONF_PARAM_STEP_MODE (dSPIN_STEP_SEL_1_128)

	/* Register : STEP_MODE - Field : SYNC_MODE and SYNC_EN */
        /* Synch. Mode settings via enum dSPIN_SYNC_SEL_TypeDef */
    #define dSPIN_CONF_PARAM_SYNC_MODE (dSPIN_SYNC_SEL_DISABLED)

        /* Register : CONFIG - field : POW_SR */
        /* Slew rate, enum dSPIN_CONFIG_POW_SR_TypeDef */
    #define dSPIN_CONF_PARAM_SR (dSPIN_CONFIG_SR_075V_us)

	/* Register : CONFIG - field : OC_SD */
        /* Over current shutwdown enabling, enum dSPIN_CONFIG_OC_SD_TypeDef */
    #define dSPIN_CONF_PARAM_OC_SD (dSPIN_CONFIG_OC_SD_DISABLE)

	/* Register : CONFIG - field : SW_MODE */
        /* External switch hard stop interrupt mode, enum dSPIN_CONFIG_SW_MODE_TypeDef */
    #define dSPIN_CONF_PARAM_SW_MODE 	(dSPIN_CONFIG_SW_USER) // (dSPIN_CONFIG_SW_HARD_STOP) ?

	/* Register : CONFIG - field : OSC_CLK_SEL */
        /* Clock setting , enum dSPIN_CONFIG_OSC_MGMT_TypeDef */
    #define dSPIN_CONF_PARAM_CLOCK_SETTING (dSPIN_CONFIG_INT_16MHZ)



///----------------------------------------------------//////


#define FALSE (0)
#define TRUE  (1)



        /* dSPIN maximum number of bytes of command and arguments to set a parameter */
        #define dSPIN_CMD_ARG_MAX_NB_BYTES (4)
        /* dSPIN command + argument bytes number */
        #define dSPIN_CMD_ARG_NB_BYTES_NOP              (1)
        #define dSPIN_CMD_ARG_NB_BYTES_RUN              (4)
        #define dSPIN_CMD_ARG_NB_BYTES_STEP_CLOCK       (1)
        #define dSPIN_CMD_ARG_NB_BYTES_MOVE             (4)
        #define dSPIN_CMD_ARG_NB_BYTES_GO_TO            (4)
        #define dSPIN_CMD_ARG_NB_BYTES_GO_TO_DIR        (4)
        #define dSPIN_CMD_ARG_NB_BYTES_GO_UNTIL         (4)
        #define dSPIN_CMD_ARG_NB_BYTES_RELEASE_SW       (1)
        #define dSPIN_CMD_ARG_NB_BYTES_GO_HOME          (1)
        #define dSPIN_CMD_ARG_NB_BYTES_GO_MARK          (1)
        #define dSPIN_CMD_ARG_NB_BYTES_RESET_POS        (1)
        #define dSPIN_CMD_ARG_NB_BYTES_RESET_DEVICE     (1)
        #define dSPIN_CMD_ARG_NB_BYTES_SOFT_STOP        (1)
        #define dSPIN_CMD_ARG_NB_BYTES_HARD_STOP        (1)
        #define dSPIN_CMD_ARG_NB_BYTES_SOFT_HIZ         (1)
        #define dSPIN_CMD_ARG_NB_BYTES_HARD_HIZ         (1)
        #define dSPIN_CMD_ARG_NB_BYTES_GET_STATUS       (1)
        /* dSPIN response bytes number */
        #define dSPIN_RSP_NB_BYTES_GET_STATUS           (2)
        /* Daisy chain command mask */
        #define DAISY_CHAIN_COMMAND_MASK (0xFA)


/** dSPIN parameter min and max values
  */
#define dSPIN_CONF_PARAM_STALL_TH_MA_MAX           ((uint16_t)(4000)) /* current in mA */

/** Register bits / masks
 */

/* dSPIN electrical position register masks */
#define dSPIN_ELPOS_STEP_MASK			((uint8_t)0xC0)
#define dSPIN_ELPOS_MICROSTEP_MASK		((uint8_t)0x3F)

/* dSPIN min speed register bit / mask */
#define dSPIN_LSPD_OPT			((uint16_t)0x1000)
#define dSPIN_MIN_SPEED_MASK	((uint16_t)0x0FFF)

/* dSPIN Sync Output frequency enabling bit */
#define dSPIN_SYNC_EN		0x80




/**
  * @brief dSPIN Init structure definition
  */
typedef struct
{
  uint32_t ABS_POS;
  uint16_t EL_POS;
  uint32_t MARK;
  uint32_t SPEED;
  uint16_t ACC;
  uint16_t DEC;
  uint16_t MAX_SPEED;
  uint16_t MIN_SPEED;
  uint16_t FS_SPD;
  uint8_t  KVAL_HOLD;
  uint8_t  KVAL_RUN;
  uint8_t  KVAL_ACC;
  uint8_t  KVAL_DEC;
  uint16_t INT_SPD;
  uint8_t  ST_SLP;
  uint8_t  FN_SLP_ACC;
  uint8_t  FN_SLP_DEC;
  uint8_t  K_THERM;
  uint8_t  ADC_OUT;
  uint8_t  OCD_TH;
  uint8_t  STALL_TH;
  uint8_t  STEP_MODE;
  uint8_t  ALARM_EN;
  uint16_t CONFIG;
  uint16_t STATUS;
}dSPIN_RegsStruct_TypeDef;

/* dSPIN Low speed optimization */
typedef enum {
	dSPIN_LSPD_OPT_OFF		=((uint16_t)0x0000),
	dSPIN_LSPD_OPT_ON		=((uint16_t)dSPIN_LSPD_OPT)
} dSPIN_LSPD_OPT_TypeDef;

/* dSPIN overcurrent threshold options */
typedef enum {
	dSPIN_OCD_TH_375mA		=((uint8_t)0x00),
	dSPIN_OCD_TH_750mA		=((uint8_t)0x01),
	dSPIN_OCD_TH_1125mA		=((uint8_t)0x02),
	dSPIN_OCD_TH_1500mA		=((uint8_t)0x03),
	dSPIN_OCD_TH_1875mA		=((uint8_t)0x04),
	dSPIN_OCD_TH_2250mA		=((uint8_t)0x05),
	dSPIN_OCD_TH_2625mA		=((uint8_t)0x06),
	dSPIN_OCD_TH_3000mA		=((uint8_t)0x07),
	dSPIN_OCD_TH_3375mA		=((uint8_t)0x08),
	dSPIN_OCD_TH_3750mA		=((uint8_t)0x09),
	dSPIN_OCD_TH_4125mA		=((uint8_t)0x0A),
	dSPIN_OCD_TH_4500mA		=((uint8_t)0x0B),
	dSPIN_OCD_TH_4875mA		=((uint8_t)0x0C),
	dSPIN_OCD_TH_5250mA		=((uint8_t)0x0D),
	dSPIN_OCD_TH_5625mA		=((uint8_t)0x0E),
	dSPIN_OCD_TH_6000mA		=((uint8_t)0x0F)
} dSPIN_OCD_TH_TypeDef;

/* dSPIN STEP_MODE register masks */
typedef enum {
	dSPIN_STEP_MODE_STEP_SEL		=((uint8_t)0x07),
	dSPIN_STEP_MODE_SYNC_SEL		=((uint8_t)0x70),
	dSPIN_STEP_MODE_SYNC_EN			=((uint8_t)0x80)
} dSPIN_STEP_MODE_Masks_TypeDef;

 /* dSPIN STEP_MODE register options */
/* dSPIN STEP_SEL options */
typedef enum {
	dSPIN_STEP_SEL_1		=((uint8_t)0x00),
	dSPIN_STEP_SEL_1_2		=((uint8_t)0x01),
	dSPIN_STEP_SEL_1_4		=((uint8_t)0x02),
	dSPIN_STEP_SEL_1_8		=((uint8_t)0x03),
	dSPIN_STEP_SEL_1_16		=((uint8_t)0x04),
	dSPIN_STEP_SEL_1_32		=((uint8_t)0x05),
	dSPIN_STEP_SEL_1_64		=((uint8_t)0x06),
	dSPIN_STEP_SEL_1_128	=((uint8_t)0x07)
} dSPIN_STEP_SEL_TypeDef;

/* dSPIN SYNC_SEL options */
typedef enum {
	dSPIN_SYNC_SEL_DISABLED		=((uint8_t)0x00),
        dSPIN_SYNC_SEL_1_2		=((uint8_t)(dSPIN_SYNC_EN|0x00)),
	dSPIN_SYNC_SEL_1		=((uint8_t)(dSPIN_SYNC_EN|0x10)),
	dSPIN_SYNC_SEL_2		=((uint8_t)(dSPIN_SYNC_EN|0x20)),
	dSPIN_SYNC_SEL_4		=((uint8_t)(dSPIN_SYNC_EN|0x30)),
	dSPIN_SYNC_SEL_8		=((uint8_t)(dSPIN_SYNC_EN|0x40)),
	dSPIN_SYNC_SEL_16		=((uint8_t)(dSPIN_SYNC_EN|0x50)),
	dSPIN_SYNC_SEL_32		=((uint8_t)(dSPIN_SYNC_EN|0x60)),
	dSPIN_SYNC_SEL_64		=((uint8_t)(dSPIN_SYNC_EN|0x70))
} dSPIN_SYNC_SEL_TypeDef;

/* dSPIN ALARM_EN register options */
typedef enum {
	dSPIN_ALARM_EN_OVERCURRENT			=((uint8_t)0x01),
	dSPIN_ALARM_EN_THERMAL_SHUTDOWN		=((uint8_t)0x02),
	dSPIN_ALARM_EN_THERMAL_WARNING		=((uint8_t)0x04),
	dSPIN_ALARM_EN_UNDER_VOLTAGE		=((uint8_t)0x08),
	dSPIN_ALARM_EN_STALL_DET_A			=((uint8_t)0x10),
	dSPIN_ALARM_EN_STALL_DET_B			=((uint8_t)0x20),
	dSPIN_ALARM_EN_SW_TURN_ON			=((uint8_t)0x40),
	dSPIN_ALARM_EN_WRONG_NPERF_CMD		=((uint8_t)0x80)
} dSPIN_ALARM_EN_TypeDef;

/* dSPIN Config register masks */
typedef enum {
	dSPIN_CONFIG_OSC_SEL					=((uint16_t)0x0007),
	dSPIN_CONFIG_EXT_CLK					=((uint16_t)0x0008),
	dSPIN_CONFIG_SW_MODE					=((uint16_t)0x0010),
	dSPIN_CONFIG_EN_VSCOMP					=((uint16_t)0x0020),
	dSPIN_CONFIG_OC_SD						=((uint16_t)0x0080),
	dSPIN_CONFIG_POW_SR						=((uint16_t)0x0300),
	dSPIN_CONFIG_F_PWM_DEC					=((uint16_t)0x1C00),
	dSPIN_CONFIG_F_PWM_INT					=((uint16_t)0xE000)
} dSPIN_CONFIG_Masks_TypeDef;

/* dSPIN Config register options */
typedef enum {
	dSPIN_CONFIG_INT_16MHZ					=((uint16_t)0x0000),
	dSPIN_CONFIG_INT_16MHZ_OSCOUT_2MHZ		=((uint16_t)0x0008),
	dSPIN_CONFIG_INT_16MHZ_OSCOUT_4MHZ		=((uint16_t)0x0009),
	dSPIN_CONFIG_INT_16MHZ_OSCOUT_8MHZ		=((uint16_t)0x000A),
	dSPIN_CONFIG_INT_16MHZ_OSCOUT_16MHZ		=((uint16_t)0x000B),
	dSPIN_CONFIG_EXT_8MHZ_XTAL_DRIVE		=((uint16_t)0x0004),
	dSPIN_CONFIG_EXT_16MHZ_XTAL_DRIVE		=((uint16_t)0x0005),
	dSPIN_CONFIG_EXT_24MHZ_XTAL_DRIVE		=((uint16_t)0x0006),
	dSPIN_CONFIG_EXT_32MHZ_XTAL_DRIVE		=((uint16_t)0x0007),
	dSPIN_CONFIG_EXT_8MHZ_OSCOUT_INVERT		=((uint16_t)0x000C),
	dSPIN_CONFIG_EXT_16MHZ_OSCOUT_INVERT	=((uint16_t)0x000D),
	dSPIN_CONFIG_EXT_24MHZ_OSCOUT_INVERT	=((uint16_t)0x000E),
	dSPIN_CONFIG_EXT_32MHZ_OSCOUT_INVERT	=((uint16_t)0x000F)
} dSPIN_CONFIG_OSC_MGMT_TypeDef;

typedef enum {
	dSPIN_CONFIG_SW_HARD_STOP		=((uint16_t)0x0000),
	dSPIN_CONFIG_SW_USER			=((uint16_t)0x0010)
} dSPIN_CONFIG_SW_MODE_TypeDef;

typedef enum {
	dSPIN_CONFIG_VS_COMP_DISABLE	=((uint16_t)0x0000),
	dSPIN_CONFIG_VS_COMP_ENABLE		=((uint16_t)0x0020)
} dSPIN_CONFIG_EN_VSCOMP_TypeDef;

typedef enum {
	dSPIN_CONFIG_OC_SD_DISABLE		=((uint16_t)0x0000),
	dSPIN_CONFIG_OC_SD_ENABLE		=((uint16_t)0x0080)
} dSPIN_CONFIG_OC_SD_TypeDef;

typedef enum {
	dSPIN_CONFIG_SR_320V_us		=((uint16_t)0x0000),
        dSPIN_CONFIG_SR_075V_us		=((uint16_t)0x0100),
	dSPIN_CONFIG_SR_110V_us		=((uint16_t)0x0200),
	dSPIN_CONFIG_SR_260V_us		=((uint16_t)0x0300)
} dSPIN_CONFIG_POW_SR_TypeDef;

typedef enum {
	dSPIN_CONFIG_PWM_DIV_1		=(((uint16_t)0x00)<<13),
	dSPIN_CONFIG_PWM_DIV_2		=(((uint16_t)0x01)<<13),
	dSPIN_CONFIG_PWM_DIV_3		=(((uint16_t)0x02)<<13),
	dSPIN_CONFIG_PWM_DIV_4		=(((uint16_t)0x03)<<13),
	dSPIN_CONFIG_PWM_DIV_5		=(((uint16_t)0x04)<<13),
	dSPIN_CONFIG_PWM_DIV_6		=(((uint16_t)0x05)<<13),
	dSPIN_CONFIG_PWM_DIV_7		=(((uint16_t)0x06)<<13)
} dSPIN_CONFIG_F_PWM_INT_TypeDef;

typedef enum {
	dSPIN_CONFIG_PWM_MUL_0_625		=(((uint16_t)0x00)<<10),
	dSPIN_CONFIG_PWM_MUL_0_75		=(((uint16_t)0x01)<<10),
	dSPIN_CONFIG_PWM_MUL_0_875		=(((uint16_t)0x02)<<10),
	dSPIN_CONFIG_PWM_MUL_1			=(((uint16_t)0x03)<<10),
	dSPIN_CONFIG_PWM_MUL_1_25		=(((uint16_t)0x04)<<10),
	dSPIN_CONFIG_PWM_MUL_1_5		=(((uint16_t)0x05)<<10),
	dSPIN_CONFIG_PWM_MUL_1_75		=(((uint16_t)0x06)<<10),
	dSPIN_CONFIG_PWM_MUL_2			=(((uint16_t)0x07)<<10)
} dSPIN_CONFIG_F_PWM_DEC_TypeDef;

/* Status Register bit masks */
typedef enum {
	dSPIN_STATUS_HIZ			=(((uint16_t)0x0001)),
	dSPIN_STATUS_BUSY			=(((uint16_t)0x0002)),
	dSPIN_STATUS_SW_F			=(((uint16_t)0x0004)),
	dSPIN_STATUS_SW_EVN			=(((uint16_t)0x0008)),
	dSPIN_STATUS_DIR			=(((uint16_t)0x0010)),
	dSPIN_STATUS_MOT_STATUS		=(((uint16_t)0x0060)),
	dSPIN_STATUS_NOTPERF_CMD	=(((uint16_t)0x0080)),
	dSPIN_STATUS_WRONG_CMD		=(((uint16_t)0x0100)),
	dSPIN_STATUS_UVLO			=(((uint16_t)0x0200)),
	dSPIN_STATUS_TH_WRN			=(((uint16_t)0x0400)),
	dSPIN_STATUS_TH_SD			=(((uint16_t)0x0800)),
	dSPIN_STATUS_OCD			=(((uint16_t)0x1000)),
	dSPIN_STATUS_STEP_LOSS_A	=(((uint16_t)0x2000)),
	dSPIN_STATUS_STEP_LOSS_B	=(((uint16_t)0x4000)),
	dSPIN_STATUS_SCK_MOD		=(((uint16_t)0x8000))
} dSPIN_STATUS_Masks_TypeDef;

/* Status Register options */
typedef enum {
	dSPIN_STATUS_MOT_STATUS_STOPPED			=(((uint16_t)0x0000)<<5),
	dSPIN_STATUS_MOT_STATUS_ACCELERATION	=(((uint16_t)0x0001)<<5),
	dSPIN_STATUS_MOT_STATUS_DECELERATION	=(((uint16_t)0x0002)<<5),
	dSPIN_STATUS_MOT_STATUS_CONST_SPD		=(((uint16_t)0x0003)<<5)
} dSPIN_STATUS_TypeDef;

/* dSPIN internal register addresses */
typedef enum {
	dSPIN_ABS_POS			=((uint8_t)0x01),
	dSPIN_EL_POS			=((uint8_t)0x02),
	dSPIN_MARK				=((uint8_t)0x03),
	dSPIN_SPEED				=((uint8_t)0x04),
	dSPIN_ACC				=((uint8_t)0x05),
	dSPIN_DEC				=((uint8_t)0x06),
	dSPIN_MAX_SPEED			=((uint8_t)0x07),
	dSPIN_MIN_SPEED			=((uint8_t)0x08),
	dSPIN_FS_SPD			=((uint8_t)0x15),
	dSPIN_KVAL_HOLD			=((uint8_t)0x09),
	dSPIN_KVAL_RUN			=((uint8_t)0x0A),
	dSPIN_KVAL_ACC			=((uint8_t)0x0B),
	dSPIN_KVAL_DEC			=((uint8_t)0x0C),
	dSPIN_INT_SPD			=((uint8_t)0x0D),
	dSPIN_ST_SLP			=((uint8_t)0x0E),
	dSPIN_FN_SLP_ACC		=((uint8_t)0x0F),
	dSPIN_FN_SLP_DEC		=((uint8_t)0x10),
	dSPIN_K_THERM			=((uint8_t)0x11),
	dSPIN_ADC_OUT			=((uint8_t)0x12),
	dSPIN_OCD_TH			=((uint8_t)0x13),
	dSPIN_STALL_TH			=((uint8_t)0x14),
	dSPIN_STEP_MODE			=((uint8_t)0x16),
	dSPIN_ALARM_EN			=((uint8_t)0x17),
	dSPIN_CONFIG			=((uint8_t)0x18),
	dSPIN_STATUS			=((uint8_t)0x19),
	dSPIN_RESERVED_REG2		=((uint8_t)0x1A),
	dSPIN_RESERVED_REG1		=((uint8_t)0x1B)
} dSPIN_Registers_TypeDef;

/* dSPIN command set */
typedef enum {
	dSPIN_NOP			=((uint8_t)0x00),
	dSPIN_SET_PARAM		=((uint8_t)0x00),
	dSPIN_GET_PARAM		=((uint8_t)0x20),
	dSPIN_RUN			=((uint8_t)0x50),
	dSPIN_STEP_CLOCK	=((uint8_t)0x58),
	dSPIN_MOVE			=((uint8_t)0x40),
	dSPIN_GO_TO			=((uint8_t)0x60),
	dSPIN_GO_TO_DIR		=((uint8_t)0x68),
	dSPIN_GO_UNTIL		=((uint8_t)0x82),
        dSPIN_GO_UNTIL_ACT_CPY  =((uint8_t)0x8A),
	dSPIN_RELEASE_SW	=((uint8_t)0x92),
	dSPIN_GO_HOME		=((uint8_t)0x70),
	dSPIN_GO_MARK		=((uint8_t)0x78),
	dSPIN_RESET_POS		=((uint8_t)0xD8),
	dSPIN_RESET_DEVICE	=((uint8_t)0xC0),
	dSPIN_SOFT_STOP		=((uint8_t)0xB0),
	dSPIN_HARD_STOP		=((uint8_t)0xB8),
	dSPIN_SOFT_HIZ		=((uint8_t)0xA0),
	dSPIN_HARD_HIZ		=((uint8_t)0xA8),
	dSPIN_GET_STATUS	=((uint8_t)0xD0),
	dSPIN_RESERVED_CMD2	=((uint8_t)0xEB),
	dSPIN_RESERVED_CMD1	=((uint8_t)0xF8)
} dSPIN_Commands_TypeDef;

/* dSPIN direction options */
typedef enum {
	FWD		=((uint8_t)0x01),
	REV		=((uint8_t)0x00)
} dSPIN_Direction_TypeDef;

/* dSPIN action options */
typedef enum {
	ACTION_RESET	=((uint8_t)0x00),
	ACTION_COPY	=((uint8_t)0x08)
} dSPIN_Action_TypeDef;
/**
  * @}
  */


/* Exported macro ------------------------------------------------------------*/
#define Speed_Steps_to_Par(steps) ((uint32_t)(((steps)*67.108864)+0.5))			/* Speed conversion, range 0 to 15625 steps/s */
#define AccDec_Steps_to_Par(steps) ((uint16_t)(((steps)*0.068719476736)+0.5))	/* Acc/Dec rates conversion, range 14.55 to 59590 steps/s2 */
#define MaxSpd_Steps_to_Par(steps) ((uint16_t)(((steps)*0.065536)+0.5))			/* Max Speed conversion, range 15.25 to 15610 steps/s */
#define MinSpd_Steps_to_Par(steps) ((uint16_t)(((steps)*4.194304)+0.5))			/* Min Speed conversion, range 0 to 976.3 steps/s */
#define FSSpd_Steps_to_Par(steps) ((uint16_t)((steps)*0.065536))				/* Full Step Speed conversion, range 7.63 to 15625 steps/s */
#define IntSpd_Steps_to_Par(steps) ((uint16_t)(((steps)*4.194304)+0.5))			/* Intersect Speed conversion, range 0 to 3906 steps/s */
#define Kval_Perc_to_Par(perc) ((uint8_t)(((perc)/0.390625)+0.5))				/* KVAL conversions, range 0.4% to 99.6% */
#define BEMF_Slope_Perc_to_Par(perc) ((uint8_t)(((perc)/0.00156862745098)+0.5))	/* BEMF compensation slopes, range 0 to 0.4% s/step */
#define KTherm_to_Par(KTherm) ((uint8_t)(((KTherm - 1)/0.03125)+0.5))			/* K_THERM compensation conversion, range 1 to 1.46875 */
#define StallTh_to_Par(StallTh) ((uint8_t)(((StallTh - 31.25)/31.25)+0.5))		/* Stall Threshold conversion, range 31.25mA to 4000mA */



/* Exported functions ------------------------------------------------------- */

void dSPIN_Init_Sem();

void dSPIN_Regs_Struct_Reset(dSPIN_RegsStruct_TypeDef* dSPIN_RegsStruct);
void dSPIN_Registers_Set(dSPIN_RegsStruct_TypeDef* dSPIN_RegsStruct);

void dSPIN_Nop();
void dSPIN_Set_Param(dSPIN_Registers_TypeDef param, uint32_t value);
uint32_t dSPIN_Get_Param( dSPIN_Registers_TypeDef param);
int32_t dSPIN_Get_Position();
void dSPIN_Run(dSPIN_Direction_TypeDef direction, uint32_t speed);
void dSPIN_Step_Clock(dSPIN_Direction_TypeDef direction);
void dSPIN_Move(dSPIN_Direction_TypeDef direction, uint32_t n_step);
void dSPIN_Go_To(int32_t abs_pos);
void dSPIN_Go_To_Dir(dSPIN_Direction_TypeDef direction, uint32_t abs_pos);
void dSPIN_Go_Until(dSPIN_Action_TypeDef action, dSPIN_Direction_TypeDef direction, uint32_t speed);
void dSPIN_Release_SW(dSPIN_Action_TypeDef action, dSPIN_Direction_TypeDef direction);
void dSPIN_Go_Home();
void dSPIN_Go_Mark();
void dSPIN_Reset_Pos();
void dSPIN_Reset_Device();
void dSPIN_Soft_Stop();
void dSPIN_Hard_Stop();
void dSPIN_Soft_HiZ();
void dSPIN_Hard_HiZ();
uint16_t dSPIN_Get_Status();

uint8_t dSPIN_Busy_SW();

uint8_t dSPIN_Write_Byte(uint8_t byte);



void dSPIN_Sel_Slave();
void dSPIN_Unsel_Slave();


#endif /* L6470_DRIVER_H_ */
