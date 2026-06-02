/* 众感 Sensemble · STM32F103C8T6 + ESP-01S WiFi 直连上报示例（进阶路径）
 * ============================================================================
 * 脱离电脑：STM32 经 ESP-01S(ESP8266, AT 固件) 用 WiFi 直接 HTTP POST 到平台。
 *
 * 接线（USART2 接 ESP-01S；USART1 留作调试打印到电脑）：
 *   ESP-01S VCC      -> 独立 3.3V 电源(≥300mA！勿用 STM32 板载 3.3V，电流不足会反复复位)
 *   ESP-01S GND      -> 公共地（与 STM32 共地）
 *   ESP-01S EN/CH_PD -> 3.3V
 *   ESP-01S RX       <- STM32 PA2 (USART2_TX)
 *   ESP-01S TX       -> STM32 PA3 (USART2_RX)
 *   传感器模拟输出    -> PA0 (ADC1_IN0)
 *   注1：ESP-01S 与 STM32F103 同为 3.3V 逻辑，UART 无需电平转换。
 *   注2：ACS712/TA12 的 0–5V 输出超过 3.3V ADC，仍需先分压再接 PA0。
 *
 * CubeMX 配置：HSE 8MHz→72MHz；USART1=115200(PA9/PA10,调试)；
 *             USART2=115200(PA2/PA3,接ESP)；ADC1_IN0=PA0。ESP-01S AT 固件常为 115200。
 *
 * ⚠️ 网络可达性：ESP-01S 基础 AT 不便做 HTTPS。设备上报建议：
 *    - 课内局域网/演示：直连后端 HTTP :8000（本例）；
 *    - 公网真实部署：走平台 MQTT(1883) 或对设备网段开放的 HTTP 入口
 *      （与端口方案一致：8000 已收口本机时，需另开设备可达的明文入口或用 1883）。
 * ============================================================================
 */
#include "main.h"
#include <stdio.h>
#include <string.h>

extern ADC_HandleTypeDef hadc1;
extern UART_HandleTypeDef huart1;   /* 调试 */
extern UART_HandleTypeDef huart2;   /* 接 ESP-01S */

/* ================== 改成你的实际参数 ================== */
#define WIFI_SSID   "your-wifi"
#define WIFI_PASS   "your-pass"
#define HOST        "149.248.16.187"
#define PORT        "8000"                /* 设备可达的 HTTP 入口 */
#define DEVICE_ID   "stm32-01"
#define DEVICE_TOK  "粘贴设备Token"
/* ===================================================== */

int fputc(int ch, FILE *f) { HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, HAL_MAX_DELAY); return ch; }

static void esp_send(const char *s) { HAL_UART_Transmit(&huart2, (uint8_t *)s, strlen(s), HAL_MAX_DELAY); }

/* 发一条 AT 命令（教学简化版：固定延时等待；工程中应解析 "OK"/">"/"ERROR"） */
static void esp_cmd(const char *cmd, uint32_t wait_ms)
{
    esp_send(cmd); esp_send("\r\n");
    printf("[AT] %s\r\n", cmd);
    HAL_Delay(wait_ms);
}

static uint16_t adc_read(void)
{
    HAL_ADC_Start(&hadc1); HAL_ADC_PollForConversion(&hadc1, 10);
    uint16_t v = HAL_ADC_GetValue(&hadc1); HAL_ADC_Stop(&hadc1); return v;
}

static void wifi_init(void)
{
    esp_cmd("AT", 500);
    esp_cmd("AT+CWMODE=1", 500);                                  /* Station 模式 */
    esp_cmd("AT+CWJAP=\"" WIFI_SSID "\",\"" WIFI_PASS "\"", 8000); /* 连 WiFi 较慢 */
}

/* 把一条 {metric,value} POST 到 /api/v1/data */
static void report(const char *metric, float value)
{
    char body[96], req[384], cmd[64];
    int blen = snprintf(body, sizeof body, "[{\"metric\":\"%s\",\"value\":%.3f}]", metric, value);
    snprintf(req, sizeof req,
        "POST /api/v1/data HTTP/1.1\r\n"
        "Host: " HOST "\r\n"
        "X-Device-Id: " DEVICE_ID "\r\n"
        "X-Device-Token: " DEVICE_TOK "\r\n"
        "Content-Type: application/json\r\n"
        "Connection: close\r\n"
        "Content-Length: %d\r\n\r\n%s", blen, body);

    esp_cmd("AT+CIPSTART=\"TCP\",\"" HOST "\"," PORT, 2000);
    snprintf(cmd, sizeof cmd, "AT+CIPSEND=%d", (int)strlen(req));
    esp_cmd(cmd, 500);
    esp_send(req);                       /* 收到 ">" 后发送 HTTP 请求（此处简化为延时） */
    HAL_Delay(1500);
    esp_cmd("AT+CIPCLOSE", 500);
    printf("[报告] %s=%.3f 已发送\r\n", metric, value);
}

int main(void)
{
    HAL_Init(); SystemClock_Config();
    MX_GPIO_Init(); MX_USART1_UART_Init(); MX_USART2_UART_Init(); MX_ADC1_Init();

    const float VREF = 3.3f, DIV = 1.0f, ACS_ZERO = 2.5f, ACS_SENS = 0.066f;
    printf("STM32F103 + ESP-01S 启动\r\n");
    wifi_init();

    while (1)
    {
        float v = adc_read() * VREF / 4095.0f * DIV;
        float current = (v - ACS_ZERO) / ACS_SENS;   /* ACS712 折算，按模块标定零点/灵敏度 */
        report("current", current);
        HAL_Delay(3000);                              /* 3s 一次，避让平台限流 */
    }
}
