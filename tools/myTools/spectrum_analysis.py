# 频谱分析
# 傅里叶变换，将时域数据转为频域数据!
# 2021.8.9

import sys
import numpy as np
from scipy.fftpack import fft


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        in_path = sys.argv[1]
        shz = int(sys.argv[2])
        out_path = sys.argv[3]
        has_title = sys.argv[4]
    except:
        stop_err("无法打开或创建文件失败！")
    pass

    in_content = [[] for i in range(12)]

    with open(in_path, 'r') as f:
        if(has_title == "t"):
            title_line = f.readline()  # 读取标题
        for line in f:
            items = line.split()  # 线上环境，不填参数
            for index, itm in enumerate(items):
                in_content[index].append(float(itm))
                pass
            pass
    clr_content = [col for col in in_content if col]  # 清除空列

    fft_ys = []  # 傅里叶
    for col in clr_content:
        fft_y = fft(col)
        fft_ys.append(fft_y)
        pass

    abs_ys = []  # 绝对值
    for col in fft_ys:
        abs_y = np.abs(col)
        abs_ys.append(abs_y)
        pass

    # nor_ys = [] #归一化
    # for col in abs_ys:
    #     nor_y = col/shz
    #     nor_ys.append(nor_y)
    #     pass

    # nor_half = [] # 折半
    # for col in nor_ys:
    #     col_half = col[range(int(len(col)/2))]
    #     nor_half.append(col_half)

    # 折半

    nor_half = []
    for col in abs_ys:
        col_half = col[range(int(len(col) / 2))]
        nor_half.append(col_half)

    # 去零
    rst = []
    for col in nor_half:
        rst.append(col[1:])

    with open(out_path, 'w') as f:
        title_items = title_line.strip().split()
        for itm in title_items:
            f.write("%s\t" % itm)
        f.write('\n')
        if len(rst) > 0 and len(rst[0]) > 0:
            row_num = len(rst[0])
        for row in range(row_num):
            for col in rst:
                f.write("%f\t" % col[row])
                pass
            f.write('\n')
            pass
        pass


if __name__ == "__main__":
    __main__()
    pass
