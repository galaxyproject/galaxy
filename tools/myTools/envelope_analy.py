# 频谱分析
# # 傅里叶变换，将时域数据转为频域数据!
# 2021.8.9

import sys
import numpy as np
from scipy.fftpack import fft


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        infile = sys.argv[1]
        div = int(sys.argv[2])  # 跨度
        outfile = sys.argv[3]
        has_title = sys.argv[4]
        spec = int(sys.argv[5])
    except:
        stop_err("无法打开或创建文件失败！")
    pass

    in_content = [[] for i in range(12)]

    with open(infile, 'r') as f:
        if(has_title == "t"):
            title_line = f.readline()  # 读取标题
        for line in f:
            items = line.split()  # 线上环境，不填参数
            for index, itm in enumerate(items):
                in_content[index].append(float(itm))
                pass
            pass
    clr_content = [col for col in in_content if col]  # 清除空列
    data = clr_content[spec]  # 当心越界

    shape_col = div
    shape_row = len(data) // div

    data = np.array(data[0:shape_row * shape_col]).reshape(shape_row, shape_col)

    ups = []
    dns = []
    for itm in data:
        ups.append(max(itm))
        dns.append(min(itm))

    fft_up = fft(ups)[1:]
    fft_dn = fft(dns)[1:]

    with open(outfile, 'w') as f:
        if has_title is 't':
            tit_itms = title_line.strip().split()
            for itm in tit_itms:
                f.write("%s\t" % itm)
            f.write("\n")
        for idx, itm in enumerate(fft_up):
            f.write('%f\t%f\n' % (itm, fft_dn[idx]))


if __name__ == "__main__":
    __main__()
    pass
