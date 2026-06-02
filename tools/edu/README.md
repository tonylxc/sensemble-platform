# 众感 Sensemble · STM32 上平台（复用现有实验装置）

复用《电气测试技术课程设计》实验装置（**STM32F103C8T6** + 37 传感器套件 + 电流互感器），
把数据送上众感平台。两条路径：

- **① PC 网关（零成本，推荐起步）**：STM32 USB 串口出数 → 本机 `pc_gateway.py` 转发到平台。
- **② ESP-01S WiFi（进阶，每套 +¥10）**：STM32 经 ESP-01S 直接联网上报，脱离电脑。

## 数据流
```
①  STM32 ─USB串口「指标,数值」→ pc_gateway.py ─HTTP→ 平台 /api/v1/data
②  STM32 ─UART→ ESP-01S ─WiFi/HTTP→ 平台 /api/v1/data
                                           └→ 时序入库 / 可视化 / 数据集(DQS)
```

## STM32F103C8T6 直接烧录配方（CubeMX + Keil + ST-Link V2）
1. **CubeMX**：芯片选 `STM32F103C8Tx`；
   - RCC：HSE = Crystal/Ceramic Resonator；时钟树 HSE 8MHz → **72MHz**（SYSCLK），ADC 分频 ≤14MHz。
   - **USART1** 115200（PA9=TX, PA10=RX）→ 调试 / 路径①接 USB-TTL 或 ST-Link VCP。
   - **ADC1_IN0 = PA0**（接传感器模拟输出）。
   - 路径②再加 **USART2** 115200（PA2=TX, PA3=RX）→ 接 ESP-01S。
   - SYS：Debug = Serial Wire（SWD）。生成 Keil MDK-ARM 工程。
2. **粘代码**：把 `stm32_uart_report.c`（路径①）或 `stm32_esp01_report.c`（路径②）的逻辑并入
   生成工程的 `main.c`（保留 CubeMX 的 `MX_*_Init()`/`SystemClock_Config()`）。
3. **Keil**：勾选 ST-Link 下载器 + “Reset and Run”，编译烧录。

### 接线表（路径①，以电流互感器为例）
| 模块 | 引脚 | STM32F103C8T6 | 说明 |
|---|---|---|---|
| ACS712/TA12 电流模块 | OUT | **经分压**→ PA0 | ⚠️ 0–5V 输出超 3.3V ADC，必须分压（如 2:3）再入，代码里 `DIV` 乘回 |
| ACS712/TA12 | VCC/GND | +5V / GND | 模块用 5V 供电 |
| USB-TTL（或 ST-Link VCP） | RXD | PA9 (USART1_TX) | 115200，连到电脑跑网关 |
| USB-TTL | GND | GND | 共地 |

### 接线表（路径②，ESP-01S）
| ESP-01S | STM32F103C8T6 | 说明 |
|---|---|---|
| VCC / EN(CH_PD) | **独立 3.3V(≥300mA)** | ⚠️ 勿用板载 3.3V，电流不足会复位 |
| GND | GND | 共地 |
| RX | PA2 (USART2_TX) | 3.3V 逻辑，无需电平转换 |
| TX | PA3 (USART2_RX) | |

## 三步上手（路径①）
1. 平台「我的设备」**注册设备** → 记下 **设备ID + Token**；
2. 按上面配方烧录 `stm32_uart_report.c`（USART1 输出 `current,0.83` 这类行）；
3. 本机：
   ```bash
   pip install pyserial requests
   python pc_gateway.py --base http://149.248.16.187:8080 --device-id <ID> --token <Token> --port COM3
   ```
   去平台「数据可视化」看曲线 →「打包数据集」算 DQS。

## 先无硬件跑通（推荐第一节课）
```bash
python pc_gateway.py --device-id d1 --token t --demo --dry-run    # 只打印 JSON 自检
python pc_gateway.py --device-id <真实ID> --token <真实Token> --demo   # 合成数据真上报
```

## 串口线协议
- 每行：`指标名,数值`（如 `current,0.83`、`light,512`、`temperature,24.6`）。
- `#` 开头或解析失败的行忽略；网关每 `--interval` 秒（默认 2s，避让限流）批量上报，自动打 `device_ts`。

## ⚠️ 关键要点
- **5V→3.3V**：ACS712/TA12 输出 0–5V，必须分压再进 STM32 的 3.3V ADC。
- **ESP-01S 供电**：独立 3.3V ≥300mA。
- **网络可达**：ESP-01S 基础 AT 不便 HTTPS；课内局域网直连 `:8000`，公网真实部署走 MQTT(1883) 或对设备开放的明文 HTTP 入口（与端口方案一致）。

## FAQ
- 端口号：Windows 设备管理器看 `COMx`；Linux 多为 `/dev/ttyUSB0`。
- 429 限流：加大 `--interval`。乱码：核对波特率（默认 115200）。
