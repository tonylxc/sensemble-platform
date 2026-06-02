"""PII / 敏感信息扫描（FR-9.2 / FR-10.2）。

对数据集名称、描述、元数据等文本做正则 + 关键词扫描，命中即在提交时拦截。
注意：只扫描文本字段，不扫描传感器数值本身。
"""
import re

ID_CARD = re.compile(r'(?<!\d)\d{17}[\dXx](?!\d)')      # 18 位身份证
PHONE = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')          # 手机号
EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')          # 邮箱
BANKCARD = re.compile(r'(?<!\d)\d{16,19}(?!\d)')         # 银行卡（粗筛）

SENSITIVE_WORDS = ["身份证", "护照", "银行卡", "信用卡", "密码", "口令",
                   "机密", "绝密", "人脸", "指纹", "车牌", "家庭住址", "考勤"]


def scan_text(*texts) -> list[str]:
    """返回命中的敏感信息类型列表（空列表表示未命中）。"""
    blob = " ".join(t for t in texts if t)
    hits = set()
    if ID_CARD.search(blob):
        hits.add("疑似身份证号")
    if PHONE.search(blob):
        hits.add("疑似手机号")
    if EMAIL.search(blob):
        hits.add("疑似邮箱地址")
    if BANKCARD.search(blob) and not ID_CARD.search(blob):
        hits.add("疑似银行卡号")
    for w in SENSITIVE_WORDS:
        if w in blob:
            hits.add(f"敏感词「{w}」")
    return sorted(hits)
