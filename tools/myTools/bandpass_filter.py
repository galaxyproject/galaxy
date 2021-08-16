# 列平均值
# 求每一列数据的区间有效值
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
        infile1 = open(sys.argv[1])
        lhz = int(sys.argv[2])
        hhz = int(sys.argv[3])
        N = int(sys.argv[4])
        shz = int(sys.argv[5])
        outfile = open(sys.argv[6], "w")
    except Exception:
        stop_err("无法打开或创建文件失败！")

    content = [[] for i in range(col_num)]  # 最多支持12个通道（列）数据
    title = infile1.readline()  # 标题
    for line in infile1:
        items = line.split()
        for index, item in enumerate(items):
            content[index].append(float(item))
            pass
        pass
    
    filted = []
    b,a = signal.butter(N,[2*lhz/shz,2*hhz/shz],'bandpass')
    # 带通滤波
    for col in content:
        if(col):
            fil = signal.filtfilt(b,a,col)
            filted.append(fil)
            pass
        pass

    title_item = title.strip().split()
    for item in title_item:
        outfile.write("%s\t"%item)
    outfile.write('\n')

    if(len(filted)>0 and len(filted[0])>0):
        row_num = len(filted[0])
        pass
    for i in range(row_num):
        for col in filted:
            outfile.write("%f\t"%col[i].real)
            pass
        outfile.write('\n')

    fft_y1 = fft(content[1][0:300])
    abs_y1 = np.abs(fft_y1 )
    fft_y2 = fft(filted[1][0:300])
    abs_y2 = np.abs(fft_y2)

    # plt.figure()
    # plt.subplot(221)
    # plt.plot(content[1][0:300])
    # plt.subplot(222)
    # plt.plot(filted[1][0:300])

    # plt.savefig("a.jpg")
         



if __name__ == "__main__":
    __main__()
    pass
