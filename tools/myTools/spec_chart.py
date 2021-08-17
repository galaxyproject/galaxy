# 绘制折线图
# 2021.8.6
# 
import sys
import matplotlib.pyplot as plt
import math
import numpy as np

max_col_num = 12

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def __main__():
    try:
        infile1 = open(sys.argv[1],'r')
        outfile = open(sys.argv[2],'wb')
        start = int(sys.argv[3])
        end = sys.argv[4]
        if(end!='end'):
            end = int(end)
        title = sys.argv[5]
        has_title = sys.argv[6]
    except Exception:
        stop_err("无法打开或者创建文件失败！")
    
    if(has_title=='t'):
        title1 = infile1.readline() #去标题

    content = [[] for i in range(max_col_num)]

    for line in infile1:
        cols = line.split()
        for index,col in enumerate(cols):
            content[index].append(float(col)) 
            pass
        pass
    
    content = [col for col in content if col]

    sub_fig_num = len(content)
    if(sub_fig_num>3):
        col_num = 3
    else:
        col_num = sub_fig_num
    row_num = sub_fig_num//col_num
    if(sub_fig_num%col_num!=0):
        row_num+=1


    plt.figure(figsize=(col_num*5,row_num*5))
    
    for idx,col in enumerate(content):
        plt.subplot(row_num,col_num,idx+1)
        x = np.linspace(0,51200/2,len(col))
        plt.plot(x,col)

    plt.savefig(outfile)

if __name__ == "__main__":
    __main__()
    pass