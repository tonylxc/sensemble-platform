"""传感器型号词典（FR-5.3）：统一元数据填写，供前端下拉与校验。"""

SENSOR_TYPES = [
    {"model": "DHT22", "metrics": ["temperature", "humidity"], "accuracy": "±0.5℃ / ±2%RH", "range": "-40~80℃ / 0~100%RH"},
    {"model": "DS18B20", "metrics": ["temperature"], "accuracy": "±0.5℃", "range": "-55~125℃"},
    {"model": "SHT30", "metrics": ["temperature", "humidity"], "accuracy": "±0.3℃ / ±2%RH", "range": "-40~125℃ / 0~100%RH"},
    {"model": "BMP280", "metrics": ["pressure", "temperature"], "accuracy": "±1hPa", "range": "300~1100hPa"},
    {"model": "MH-Z19", "metrics": ["co2"], "accuracy": "±50ppm+5%", "range": "0~5000ppm"},
    {"model": "MQ-135", "metrics": ["air_quality", "co2"], "accuracy": "—", "range": "10~1000ppm"},
    {"model": "BH1750", "metrics": ["illuminance"], "accuracy": "±20%", "range": "1~65535lx"},
    {"model": "PMS5003", "metrics": ["pm2_5", "pm10"], "accuracy": "±10%", "range": "0~500μg/m³"},
    {"model": "INA219", "metrics": ["voltage", "current", "power"], "accuracy": "±0.5%", "range": "0~26V / ±3.2A"},
    {"model": "其他/自定义", "metrics": [], "accuracy": "", "range": ""},
]
