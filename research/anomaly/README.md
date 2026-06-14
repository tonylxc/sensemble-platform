# 数据质量感知的可解释多元时序异常检测 · P1 脚手架

第一篇选题的最小可验证实现。核心创新点：**DQS×异常 联合判别**——把数据质量评估与
异常检测耦合，显式区分「真实系统异常」与「数据质量异常（掉线/漂移/饱和）」，压低误报。

## 目录
| 文件 | 作用 |
|---|---|
| `datasets.py` | 合成多元时序 + 真异常/质量异常可控注入；`load_smd()` 接入 SMD 真数据 |
| `quality.py` | 质量门控：从数据质量签名算逐点风险 `r_t` 与门控 `g_t=1-r_t` |
| `detectors.py` | 无监督基线：稳健 z 分数、孤立森林、PCA 重构 |
| `metrics.py` | 真异常 F1 / point-adjust F1 / AUC-PR + **质量误报率** |
| `experiment.py` | 朴素 vs 质量门控 对比，多种子平均，打印结果表 |
| `tests/` | 把核心论断编码为回归测试 |

## 运行
```bash
# 依赖（本机若已有 numpy/sklearn/pandas 可跳过）
pip install -r research/anomaly/requirements.txt

# 出第一批对比结果（合成可控数据）
python research/anomaly/experiment.py

# 回归测试（验证“门控降低质量误报且不伤真异常”）
python -m pytest research/anomaly/tests -q
```

## 方法（与选题论证对应）
逐点质量风险 `r_t∈[0,1]`，门控 `g_t = 1 - r_t`；检测器异常分 `s_t`：

- 真异常分 `s̃_t = g_t · s_t`（质量伪迹处 g 低 → 被抑制，减少误报）
- 质量异常 由 `r_t` 高直接标记，单独输出

评测同时报 **真异常 PA-F1 / 召回** 与 **质量误报率**：期望门控在前者基本不变的前提下
显著降低后者。

## 接入 SMD 真数据
下载 OmniAnomaly 的 `ServerMachineDataset/`（train/test/test_label，逗号分隔），然后：
```python
from research.anomaly.datasets import load_smd
X_train, X_test, y_test = load_smd("/path/to/ServerMachineDataset", "machine-1-1")
```
把 `experiment.py` 的数据源换成 `X_test`、标签换成 `y_test` 即可在真实服务器遥测上复现。
SMD 本身是服务器多元遥测，天然桥接后续 **C3 算电协同**。

## 路线（下一刀）
1. 深度时序基线：AE/VAE/USAD、TCN/Transformer（本机已具备 torch）。
2. 平台集成：异常检测+质量门控服务接入 ingest，结果上大屏。
3. 真数据：SMD/SMAP/MSL 跑全量 + 跨数据集泛化。
