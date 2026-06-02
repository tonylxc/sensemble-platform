"""元数据辅助接口（FR-5.3）：传感器型号词典。"""
from fastapi import APIRouter
from ..meta_dict import SENSOR_TYPES

router = APIRouter()


@router.get("/sensor-types")
def sensor_types():
    return SENSOR_TYPES
