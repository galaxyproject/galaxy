# 列平均值
# 求每一列数据的区间平均值
# 2021.8.4

import sys
from numpy import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        infile1 = open(sys.argv[1])
        v2 = int(sys.argv[2])
        outfile = open(sys.argv[3],"w")
        has_title = sys.argv[4]
    except Exception:
        stop_err("无法打开或创建文件失败！")
    sec = int(v2)
    if(has_title is 't'):
        line = infile1.readline()#去标题
    while True:
        counters = [[] for i in range(12)]
        num = 0
        result = []
        for i in range(sec):
            line = infile1.readline()
            if not line:
                break
            items = line.split()
            num += 1
            for index, v in enumerate(items):
                counters[index].append(float(v))
                pass
            pass
        if num>0:
            for col in counters:
                if col:
                    outfile.write("%f\t"%mean(col))
            outfile.write("\n")
        else:
            break

if __name__ == "__main__":
    __main__()
    pass
    
