# 求平均值
# 计算输入文件中所有值的平均值
# 2021.8.4


from os import times
import sys


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    pass

 

def __main__():
    try:
        infile1 = open(sys.argv[1])
        outfile = open(sys.argv[2],'w')
    except Exception:
        stop_err("无法打开或者创建文件")
    
    counter = 0
    timer = 0
    for line in infile1:
        items = line.split()
        for item in items:
            counter += int(item)
            timer += 1

    print(counter/timer,file=outfile)

    pass


if __name__ == "__main__":
    __main__()
    pass