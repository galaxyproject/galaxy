# -*- coding: utf-8 -*-

# 相关性分析
# # 傅里叶变换，将时域数据转为频域数据!
# 2021.8.9

import sys
import json
import matplotlib.pyplot as plt




def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        infile = sys.argv[1]    # input
        output = sys.argv[2]  # output
        title = sys.argv[3] # title
    
    except:
        stop_err("无法打开或创建文件失败！")
    pass

    with open(infile,'r') as f:
        json_data = json.load(f)
    
    cols_data = json_data['data']
    titles = json_data['title']
    pears = json_data["Pearson"]
    spear = json_data["Spearman"]
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.set_title(title)
    ax.scatter(cols_data[0],cols_data[1],color="green",marker='+')
    ax.set_xlabel(titles[0])
    ax.set_ylabel(titles[1])
    ax.text(0.7,0.9,"Pearson:%f\nSpearman:%f"%(pears,spear),transform=ax.transAxes,fontdict={'size': '11', 'color': 'coral'})
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    with open(output,'wb') as f:
        plt.savefig(f)
        # f.write(title)
if __name__ == "__main__":
    __main__()
    pass
