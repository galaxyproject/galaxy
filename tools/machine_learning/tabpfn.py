#!/usr/bin/env python
"""
用于使用TabPFN进行二分类任务的Galaxy工具。

usage: %prog [options] input_file output_metrics output_train output_test output_train_y output_test_y output_predictions
  -l, --target_column=N: 目标列的名称
  -s, --split_ratio=N: 测试集占总数据的比例 (0-1 之间)
  -r, --random_seed=N: 随机数种子
"""

import sys
import os
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from bx.cookbook import doc_optparse

# 将TabPFN添加到路径中
tabpfn_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'TabPFN-main'))
sys.path.append(tabpfn_path)
from tools.machine_learning.tabpfn import TabPFNClassifier

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit(1)

def __main__():
    # 解析命令行参数
    options, args = doc_optparse.parse(__doc__)
    
    try:
        input_file = args[0]
        output_metrics = args[1]
        output_train = args[2]
        output_test = args[3]
        output_train_y = args[4]
        output_test_y = args[5]
        output_predictions = args[6]
        
        target_column = options.target_column
        split_ratio = float(options.split_ratio)
        random_seed = int(options.random_seed)
        
        if not (0 < split_ratio < 1):
            stop_err("测试集比例必须在0到1之间")
            
    except Exception as e:
        stop_err("参数解析错误: %s" % str(e))
    
    try:
        # 读取数据
        data = pd.read_csv(input_file)
        
        # 检查目标列是否存在
        if target_column not in data.columns:
            stop_err("目标列 '%s' 不在输入文件中" % target_column)
        
        # 准备特征和目标变量
        X = data.drop(target_column, axis=1)
        y = data[target_column]
        
        # 分割数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=split_ratio, random_state=random_seed
        )
        
        # 初始化分类器
        clf = TabPFNClassifier(device='cpu', N_ensemble_configurations=32)
        
        # 训练模型
        clf.fit(X_train, y_train)
        
        # 预测概率和类别
        prediction_probs = clf.predict_proba(X_test)
        predictions = clf.predict(X_test)
        
        # 计算评估指标
        metrics = {}
        metrics["准确率"] = accuracy_score(y_test, predictions)
        
        # 如果是二分类问题，计算ROC AUC
        unique_classes = np.unique(y)
        if len(unique_classes) == 2:
            metrics["ROC AUC"] = roc_auc_score(y_test, prediction_probs[:, 1])
            metrics["精确率"] = precision_score(y_test, predictions)
            metrics["召回率"] = recall_score(y_test, predictions)
            metrics["F1分数"] = f1_score(y_test, predictions)
            
        # 输出评估指标
        with open(output_metrics, 'w') as f_metrics:
            f_metrics.write("指标\t值\n")
            for metric_name, metric_value in metrics.items():
                f_metrics.write(f"{metric_name}\t{metric_value:.4f}\n")
        
        # 输出训练集和测试集
        X_train.to_csv(output_train, index=False)
        X_test.to_csv(output_test, index=False)
        
        # 输出训练集和测试集目标值
        pd.DataFrame(y_train).to_csv(output_train_y, index=False)
        pd.DataFrame(y_test).to_csv(output_test_y, index=False)
        
        # 输出预测结果
        prediction_df = pd.DataFrame({
            "实际值": y_test,
            "预测值": predictions
        })
        if len(unique_classes) == 2:
            prediction_df["预测概率"] = prediction_probs[:, 1]
        
        prediction_df.to_csv(output_predictions, index=False)
        
    except Exception as e:
        stop_err("执行错误: %s" % str(e))

if __name__ == "__main__":
    __main__()
