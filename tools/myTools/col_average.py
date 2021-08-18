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
        in_f = open(sys.argv[1])
        div = int(sys.argv[2])
        out_f = open(sys.argv[3], "w")
        has_title = sys.argv[4]
    except Exception:
        stop_err("无法打开或创建文件失败！")
    if(has_title is 't'):
        title_line = in_f.readline()  # 去标题
        title_itms = title_line.strip().split()
        for itm in title_itms:
            out_f.write("%s\t" % itm)
        out_f.write('\n')
    while True:
        counters = [[] for i in range(12)]
        num = 0
        result = []
        for i in range(div):
            line = in_f.readline()
            if not line:
                break
            items = line.split()
            num += 1
            for index, v in enumerate(items):
                counters[index].append(float(v))
                pass
            pass
        if num > 0:
            for col in counters:
                if col:
                    out_f.write("%f\t" % mean(col))
            out_f.write("\n")
        else:
            break


if __name__ == "__main__":
    __main__()
    pass
