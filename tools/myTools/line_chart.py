# 绘制折线图
# 2021.8.6
# 
import sys
import matplotlib.pyplot as plt

max_col_num = 12

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def __main__():
    try:
        infile1 = open(sys.argv[1])
        outfile = open(sys.argv[2],'wb')
        start = int(sys.argv[3])
        end = int(sys.argv[4])
        title = sys.argv[5]
    except Exception:
        stop_err("无法打开或者创建文件失败！")
    
    title1 = infile1.readline() #去标题

    content = [[] for i in range(max_col_num)]

    for line in infile1:
        cols = line.split()
        for index,col in enumerate(cols):
            content[index].append(float(col)) 
            pass
        pass
    plt.title(title)
    for col in content:
        if(col):
            plt.plot(col[start:end])

    plt.savefig(outfile)

if __name__ == "__main__":
    __main__()
    pass