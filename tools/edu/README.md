# 众感 Sensemble · STM32 零硬件上报（PC 网关）

复用现有《电气测试技术课程设计》实验装置（STM32 + 37 传感器套件 + 电流互感器），
**不加任何联网硬件**，把数据送上众感平台。学生专注"传感器与测量"，PC 当网关转发。

## 数据流
```
STM32 ──USB串口逐行「指标,数值」──> 本机 pc_gateway.py ──HTTP──> 平台 /api/v1/data
                                                              └─> 时序入库 / 可视化 / 数据集(DQS)
```

## 三步上手
1. 平台「我的设备」**注册一个设备**，记下 **设备ID** 与一次性 **Token**。
2. STM32 烧录 `stm32_uart_report.c` 的逻辑：USART1 @115200 输出形如 `current,0.83` 的行。
   - ⚠️ ACS712 / TA12-200 输出 **0–5V，超过 STM32 3.3V ADC**，须先**分压**再入 ADC（详见 .c 注释）。
   - 0–3.3V 的传感器可直接接 ADC/GPIO。
3. 本机装依赖并运行网关：
   ```bash
   pip install pyserial requests
   python pc_gateway.py --base http://149.248.16.187:8080 \
          --device-id <设备ID> --token <Token> --port COM3
   ```
   然后去平台「数据可视化」看曲线，再「打包数据集」算 DQS。

## 先无硬件跑通（推荐第一节课）
```bash
python pc_gateway.py --device-id d1 --token t --demo --dry-run   # 只打印 JSON，自检
python pc_gateway.py --device-id <真实ID> --token <真实Token> --demo   # 合成数据真上报
```

## 串口线协议
- 每行一条：`指标名,数值`，如 `current,0.83`、`light,512`、`temperature,24.6`。
- 以 `#` 开头或无法解析的行被忽略。
- 网关每 `--interval` 秒（默认 2s，避开平台限流）批量上报一次，并给每点打 `device_ts` 时间戳。

## 常见问题
- **端口号**：Windows 在设备管理器看 `COMx`；Linux 多为 `/dev/ttyUSB0`。
- **429 限流**：加大 `--interval`。
- **乱码**：确认串口波特率与 STM32 一致（默认 115200）。
- 进阶（脱离电脑）：给 STM32 串口挂 ESP-01S 走 WiFi 直连上报——需要时我再给例程。
