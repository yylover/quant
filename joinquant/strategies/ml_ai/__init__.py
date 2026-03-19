# -*- coding: utf-8 -*-
"""
机器学习AI选股策略包 (ML/AI Stock Selection Strategies)
======================================================

本目录包含基于机器学习和深度学习技术实现的聚宽交易策略。

机器学习选股策略的核心思想：
通过机器学习模型（XGBoost、LightGBM、LSTM、CNN等）从大量历史数据中
学习股票的收益模式，预测未来收益率或涨跌方向，选择预测表现最优的股票
构建组合，配合择时信号控制仓位，实现"数据驱动+智能预测"的投资逻辑。

包含策略（共6个）：
-----------------

1. xgboost_regression.py - XGBoost回归选股策略
   - 模型：XGBoost回归（梯度提升决策树）
   - 目标：预测未来20日收益率
   - 特征：基本面(10) + 技术面(10) + 情绪面(5) = 25个因子
   - 持股数量：15只
   - 策略特点：处理非线性能力强，预测准确率高
   - 适用场景：中短期投资，因子关系复杂

2. lightgbm_classification.py - LightGBM分类选股策略
   - 模型：LightGBM分类（轻量级梯度提升框架）
   - 目标：预测涨跌方向（买入/持有/卖出）
   - 特征：基本面(8) + 技术面(8) + 情绪面(4) = 20个因子
   - 持股数量：15只
   - 策略特点：训练速度快，分类准确率高
   - 适用场景：中短期投资，注重涨跌方向

3. rf_feature_importance.py - 随机森林特征重要性策略
   - 模型：随机森林回归（集成学习）
   - 目标：计算特征重要性并选股
   - 特征：基本面(10) + 技术面(12) + 情绪面(5) + 风格(3) = 30个因子
   - 持股数量：15只
   - 策略特点：特征重要性可视化，自动筛选有效因子
   - 适用场景：因子挖掘，特征工程

4. lstm_prediction.py - LSTM时序预测策略
   - 模型：LSTM神经网络（长短期记忆网络）
   - 目标：基于时序数据预测未来收益率
   - 特征：价格(5) × 60天 = 300个时序特征
   - 持股数量：15只
   - 策略特点：捕获时序依赖，处理长期记忆
   - 适用场景：时序建模，趋势预测

5. cnn_kline.py - CNN K线图识别策略
   - 模型：CNN卷积神经网络（图像识别）
   - 目标：从K线图中识别形态并预测涨跌
   - 特征：30日K线图(64×64×3) + 手动K线形态
   - 持股数量：15只
   - 策略特点：图像识别，自动提取形态特征
   - 适用场景：技术分析，形态识别

6. pca_factor.py - PCA因子提取策略
   - 模型：PCA主成分分析（无监督降维）
   - 目标：从20个因子中提取5个主成分
   - 特征：基本面(10) + 技术面(6) + 风格(4) = 20个因子 → 5个主成分
   - 持股数量：15只
   - 策略特点：降维压缩，消除多重共线性
   - 适用场景：因子正交化，风险分散

适用场景：
---------
- 数据丰富：需要大量历史数据训练模型
- 因子众多：传统多因子策略因子过多导致过拟合
- 关系复杂：因子与收益之间存在非线性关系
- 中短期：机器学习更适合中短期预测
- 量化研究：需要系统性挖掘因子

风险提示：
---------
- 过拟合风险：模型可能过度拟合历史数据
- 数据依赖：需要大量高质量的历史数据
- 黑箱模型：部分模型（如深度学习）解释性较差
- 计算资源：模型训练需要较强的计算能力
- 市场变化：模型可能无法适应市场结构变化
- 维护成本：模型需要定期重新训练

改进方向：
---------
1. 模型层面：
   - 集成多个模型（Stacking、Voting）
   - 超参数优化（网格搜索、贝叶斯优化）
   - 模型融合（结合多个模型的预测）

2. 特征层面：
   - 增加更多因子（情绪因子、宏观因子）
   - 特征交互（创建特征组合）
   - 特征选择（自动筛选重要特征）

3. 交易层面：
   - 动态仓位管理
   - 止损机制
   - 分批建仓

使用示例：
---------
在聚宽平台回测时，直接使用对应的策略文件即可。

如需调整参数，修改各策略文件中 set_parameter() 函数中的全局变量。

注意事项：
---------
1. 依赖库安装：
   - XGBoost：pip install xgboost
   - LightGBM：pip install lightgbm
   - TensorFlow（LSTM/CNN）：pip install tensorflow
   - Scikit-learn：pip install scikit-learn

2. 聚宽平台限制：
   - 聚宽可能不支持TensorFlow
   - 深度学习模型可能运行缓慢
   - 建议优先使用XGBoost和LightGBM

3. 训练时间：
   - 首次运行需要训练模型，可能较慢
   - 后续运行会使用已训练模型，速度较快

参考资料：
---------
1. XGBoost文档：https://xgboost.readthedocs.io/
2. LightGBM文档：https://lightgbm.readthedocs.io/
3. TensorFlow文档：https://www.tensorflow.org/
4. Scikit-learn文档：https://scikit-learn.org/
5. 量化投资：策略与技术（陆一鸣）
6. 机器学习与量化投资（蔡立耑）
"""

# 导入所有策略
from .xgboost_regression import initialize as init_xgboost_regression
from .lightgbm_classification import initialize as init_lightgbm_classification
from .rf_feature_importance import initialize as init_rf_feature_importance
from .lstm_prediction import initialize as init_lstm_prediction
from .cnn_kline import initialize as init_cnn_kline
from .pca_factor import initialize as init_pca_factor

# 策略映射表（方便按名称调用）
STRATEGY_MAP = {
    'xgboost_regression': init_xgboost_regression,  # XGBoost回归选股
    'lightgbm_classification': init_lightgbm_classification,  # LightGBM分类选股
    'rf_feature_importance': init_rf_feature_importance,  # 随机森林特征重要性
    'lstm_prediction': init_lstm_prediction,  # LSTM时序预测
    'cnn_kline': init_cnn_kline,  # CNN K线图识别
    'pca_factor': init_pca_factor,  # PCA因子提取
}
