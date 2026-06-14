import os
import sys

# 把仓库根加入 sys.path，使 `research.anomaly.*` 可导入（pytest 从任意目录运行均可）。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
