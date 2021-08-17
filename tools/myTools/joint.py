# 文件拼接
# 2021.8.4
# 
import sys

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def __main__():
    try:
        infile1 = open(sys.argv[1])
        infile2 = open(sys.argv[2])
        outfile = open(sys.argv[3],'w')
        has_title1 = sys.argv[4]
        has_title2 = sys.argv[5]
    except Exception:
        stop_err("无法打开或者创建文件失败！")
    if(has_title1=='t'):
        title1 = infile1.readline()
    if(has_title2=='f'):
        title2 = infile2.readline()#去标题

    # 不留标题
    # title_items = title1.strip().split()
    # for item in title_items:
    #     outfile.write("%s\t"%item)
    # outfile.write('\n')

    for line in infile1:
        print(line,file=outfile)
        pass
    for line in infile2:
        print(line,file=outfile)
        pass




if __name__ == "__main__":
    __main__()
    pass