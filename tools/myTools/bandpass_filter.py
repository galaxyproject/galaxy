# 带通滤波
# 针对每列数据进行滤波，并生成对应的滤波结果写入文件
# 2021.8.4

from os import times
import sys
import numpy as np
from scipy.fftpack import fft, ifft
import matplotlib.pyplot as plt
from scipy import signal

col_num = 12  # 常量


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        in_path = sys.argv[1]   # 输入路径
        lhz = int(sys.argv[2])  # 频率下限
        hhz = int(sys.argv[3])  # 频率上限
        N = int(sys.argv[4])    # 滤波阶数
        shz = int(sys.argv[5])  # 采样频率
        out_path = sys.argv[6]  # 输出文件名
        has_title = sys.argv[7] # 数据是否存在标题
    except Exception:
        stop_err("无法打开或创建文件失败！")

    content = [[] for i in range(col_num)]  # 最多支持12个通道（列）数据

    with open(in_path, 'r') as in_f:
        if(has_title is 't'):
            title_line = in_f.readline()  # 标题行
        for line in in_f:
            items = line.split()
            for index, item in enumerate(items):
                content[index].append(float(item))
                pass
            pass
    clr_content = [col for col in content if col]
    filted = []
    b, a = signal.butter(N, [2 * lhz / shz, 2 * hhz / shz], 'bandpass')

    # 带通滤波
    for col in clr_content:
        fil = signal.filtfilt(b, a, col)
        filted.append(fil)
        pass

    # 标题
    

    if(len(filted) > 0 and len(filted[0]) > 0):
        row_num = len(filted[0])
        pass
    with open(out_path, 'w') as out_f:
        if has_title is 't':
            title_items = title_line.strip().split()
            for item in title_items:
                out_f.write("%s\t" % item)
            out_f.write('\n')

        for i in range(row_num):
            for col in filted:
                out_f.write("%f\t" % col[i].real)
                pass
            out_f.write('\n')
    pass  # end of __main()__

if __name__ == "__main__":
    __main__()
    pass
