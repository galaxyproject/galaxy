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
    except Exception:
        stop_err("无法打开或者创建文件失败！")
    
    title1 = infile1.readline()
    title2 = infile2.readline()#去标题

    title_items = title1.strip().split()
    for item in title_items:
        outfile.write("%s\t"%item)
    outfile.write('\n')

    for line in infile1:
        print(line,file=outfile)
        pass
    for line in infile2:
        print(line,file=outfile)
        pass




if __name__ == "__main__":
    __main__()
    pass