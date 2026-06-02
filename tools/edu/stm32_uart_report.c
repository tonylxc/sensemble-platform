/* 众感 Sensemble · STM32 采集 + 串口上报示例（STM32F103C8T6, HAL 风格）
 * ----------------------------------------------------------------------------
 * 唯一要紧的“契约”：通过 USART1 以每行  指标,数值\r\n  输出即可，
 * PC 端 pc_gateway.py 负责把它转发到平台。所以你现有的 STM32 代码
 * （HAL / 标准库 / Arduino-STM32 都行）只要按这个格式 printf 串口即可。
 *
 * 接线：USART1_TX = PA9  →  USB转串口 / ST-Link 的 VCP（115200-8-N-1）
 *       模拟传感器输出   →  ADC1_IN0 = PA0
 *
 * ⚠️ 重要：ACS712 / TA12-200 电流模块输出 0–5V，超过 STM32 的 3.3V ADC 量程！
 *    必须先经分压（如 R1:R2 做 2:3 分压把 5V→3.3V）再接 PA0，并在公式里乘回
 *    分压比；否则读数削顶，甚至损伤引脚。0–3.3V 输出的传感器可直接接。
 * ----------------------------------------------------------------------------
 */
#include "main.h"
#include <stdio.h>

extern ADC_HandleTypeDef hadc1;     /* CubeMX 生成：PA0 = ADC1_IN0 */
extern UART_HandleTypeDef huart1;   /* CubeMX 生成：USART1 @115200 */

/* 让 printf 输出走 USART1 */
int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, HAL_MAX_DELAY);
    return ch;
}

/* 读一次 ADC1，返回 0~4095 */
static uint16_t adc_read(void)
{
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint16_t v = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    return v;
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();           /* CubeMX 生成 */
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_ADC1_Init();

    const float VREF = 3.3f;        /* ADC 参考电压 */
    const float DIV  = 1.0f;        /* 分压比：若做了 2:3 分压读 5V 传感器，改成 5.0/3.3 */
    const float ACS_ZERO = 2.5f;    /* ACS712 零点(分压前) */
    const float ACS_SENS = 0.066f;  /* ACS712-30A 灵敏度 66mV/A，按实际模块标定 */

    while (1)
    {
        uint16_t raw  = adc_read();
        float v_adc   = raw * VREF / 4095.0f;     /* ADC 测得电压 */
        float v_real  = v_adc * DIV;              /* 还原到分压前的真实电压 */

        /* 示例1：ACS712 折算电流（按你的模块标定零点与灵敏度） */
        float current = (v_real - ACS_ZERO) / ACS_SENS;
        printf("current,%.3f\r\n", current);

        /* 示例2：直接上报 ADC 电压（任意模拟传感器通用，先跑通管道） */
        printf("adc_volt,%.3f\r\n", v_real);

        HAL_Delay(1000);            /* 1 秒一次，配合网关 --interval（默认 2s） */
    }
}
