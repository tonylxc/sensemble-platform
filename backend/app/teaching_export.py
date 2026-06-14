"""教学数据导出工具：学生作答 + 设备传感器时间序列。

支持 CSV 和 Excel 输出，用于教学质量评估和科研分析。
"""
import io
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .teaching import StudentLog, Quiz, CourseNode, LogKind


class TeachingDataExporter:
    """导出学生学习数据及关联的设备传感器数据。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_student_logs(
        self,
        student_id: Optional[int] = None,
        course_code: Optional[str] = None,
        format: str = 'csv'
    ) -> Tuple[bytes, str, str]:
        """
        导出学生作答数据及完整的传感器时间序列。

        Args:
            student_id: 学生 ID（可选，不指定则导出所有学生）
            course_code: 课程代码（可选）
            format: 输出格式（'csv' 或 'xlsx'）

        Returns:
            (文件内容, MIME 类型, 文件名)
        """
        # 第 1 步：查询学生作答记录（仅 quiz_answer 类型）
        query = select(StudentLog).where(
            StudentLog.kind == LogKind.quiz_answer
        )
        if student_id:
            query = query.where(StudentLog.user_id == student_id)

        logs = (await self.db.execute(query)).scalars().all()

        if not logs:
            # 返回空文件
            df = pd.DataFrame()
            return self._export_dataframe(df, format)

        # 第 2 步：为每条记录关联 Quiz、CourseNode、User、Device、SensorData
        rows = []
        for log in logs:
            # 获取 Quiz 和 CourseNode 信息
            quiz = await self.db.get(Quiz, log.quiz_id)
            node = await self.db.get(CourseNode, log.node_id)

            # 获取用户信息
            user = await self.db.get(models.User, log.user_id)

            # 基础行信息
            base_row = {
                'student_id': log.user_id,
                'username': user.username if user else 'Unknown',
                'course_code': node.course_code if node else 'N/A',
                'knowledge_point': node.title if node else 'N/A',
                'quiz_type': quiz.qtype.value if quiz else 'N/A',
                'quiz_stem': quiz.stem if quiz else 'N/A',
                'student_answer': str(log.answer) if log.answer else '',
                'is_correct': log.is_correct,
                'score': log.score,
                'answered_at': log.created_at.isoformat() if log.created_at else 'N/A',
                'device_id': log.device_id
            }

            # 如果有关联设备，查询该时段的传感器数据
            sensor_rows = []
            if log.device_id and log.created_at:
                sensor_rows = await self._get_sensor_data_around(
                    device_id=log.device_id,
                    center_time=log.created_at,
                    window_minutes=5  # 答题前后各 5 分钟
                )

            if sensor_rows:
                # 为每条传感器记录单独生成一行（展开）
                for sensor_row in sensor_rows:
                    merged_row = {**base_row, **sensor_row}
                    rows.append(merged_row)
            else:
                # 无传感器数据，单独一行
                rows.append(base_row)

        # 第 3 步：生成 DataFrame 和输出
        df = pd.DataFrame(rows)

        # 列顺序优化（学生信息 → 作答数据 → 传感器数据）
        column_order = [
            'student_id', 'username', 'course_code', 'knowledge_point',
            'quiz_type', 'quiz_stem', 'student_answer', 'is_correct', 'score',
            'answered_at', 'device_id',
            'sensor_ts', 'metric', 'value', 'raw'  # 传感器列（如果存在）
        ]
        # 仅保留存在的列
        column_order = [c for c in column_order if c in df.columns]
        if column_order:
            df = df[column_order]

        return self._export_dataframe(df, format)

    async def _get_sensor_data_around(
        self,
        device_id: str,
        center_time: datetime,
        window_minutes: int = 5
    ) -> List[dict]:
        """
        获取某个时间点前后的传感器数据。

        Args:
            device_id: 设备 ID
            center_time: 中心时间（通常是答题时间）
            window_minutes: 前后窗口大小（分钟）

        Returns:
            传感器数据行列表
        """
        start_time = center_time - timedelta(minutes=window_minutes)
        end_time = center_time + timedelta(minutes=window_minutes)

        query = select(models.SensorData).where(
            models.SensorData.device_id == device_id,
            models.SensorData.ts >= start_time,
            models.SensorData.ts <= end_time
        ).order_by(models.SensorData.ts)

        sensor_data = (await self.db.execute(query)).scalars().all()

        rows = []
        for sd in sensor_data:
            rows.append({
                'sensor_ts': sd.ts.isoformat() if sd.ts else 'N/A',
                'metric': sd.metric,
                'value': sd.value,
                'raw': str(sd.raw) if sd.raw else None
            })

        return rows

    def _export_dataframe(self, df: pd.DataFrame, format: str) -> Tuple[bytes, str, str]:
        """
        将 DataFrame 导出为 CSV 或 Excel。

        Args:
            df: 数据框
            format: 'csv' 或 'xlsx'

        Returns:
            (文件字节, MIME 类型, 文件名)
        """
        output = io.BytesIO()

        if format == 'csv':
            csv_str = df.to_csv(index=False, encoding='utf-8-sig')
            output.write(csv_str.encode('utf-8'))
            mime = 'text/csv'
            filename = 'teaching_export.csv'
        else:  # xlsx
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='学生作答数据', index=False)

                # 格式化 Excel
                workbook = writer.book
                worksheet = writer.sheets['学生作答数据']

                # 调整列宽
                for col in worksheet.columns:
                    max_len = 0
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_len:
                                max_len = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_len + 2, 50)
                    worksheet.column_dimensions[col[0].column_letter].width = adjusted_width

            output.seek(0)
            mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = 'teaching_export.xlsx'

        return output.getvalue(), mime, filename
