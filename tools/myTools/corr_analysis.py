# 相关性分析
# 傅里叶变换，将时域数据转为频域数据!
# 2021.8.9

import sys
import numpy as np
import json
from scipy.stats import spearmanr, pearsonr


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        infile = sys.argv[1]    # input
        output = sys.argv[2]  # output
        has_title = sys.argv[3]  # has_title
        idx1 = int(sys.argv[4])  # 列编号1
        idx2 = int(sys.argv[5])  # 列编号2
        div = int(sys.argv[6])   # 采样跨度
    except:
        stop_err("无法打开或创建文件失败！")
    pass

    in_content = [[] for i in range(12)]

    with open(infile, 'r') as f:
        if(has_title == "t"):
            title = f.readline()  # 读取标题
        for line in f:
            items = line.split()  # 线上环境，不填参数
            for index, itm in enumerate(items):
                in_content[index].append(float(itm))
                pass
            pass
    title_split = title.split()
    clr_content = [col for col in in_content if col]  # 清除空列

    ori1 = clr_content[idx1]
    ori2 = clr_content[idx2]

    col1 = []
    col2 = []

   
    index = 0
    while(index<len(ori1)):      # 采样
        col1.append(ori1[index]*1000)
        col2.append(ori2[index]*1000)
        index+=div
    
    title1 = title_split[idx1]+"(*1000)"
    title2 = title_split[idx2]+"(*1000)"

    rst = {}
    rst['title'] = [title1, title2]
    rst['data'] = [col1, col2]

    spear = spearmanr(col1, col2)
    pears = pearsonr(col1, col2)

    rst["Spearman"] = spear[0]
    rst["Pearson"] = pears[0]

    jstr = json.dumps(rst)
    with open(output, 'w') as f:
        f.write(jstr)


if __name__ == "__main__":
    __main__()
    pass
