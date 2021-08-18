# 文件拼接
# 2021.8.4
#
import sys


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def __main__():
    try:
        in_path1 = sys.argv[1]
        in_path2 = sys.argv[2]
        out_path = sys.argv[3]
        has_title1 = sys.argv[4]
        has_title2 = sys.argv[5]
    except Exception:
        stop_err("无法打开或者创建文件失败！")

    in_f1 = open(in_path1, 'r')
    in_f2 = open(in_path2, 'r')
    out_f = open(out_path, 'w')

    if(has_title1 == 't'):
        title_line1 = in_f1.readline()
        title_itms = title_line1.strip().split()
        for itm in title_itms:
            out_f.write("%s\t" % itm)
        out_f.write('\n')
    if(has_title2 == 'f'):
        title_line2 = in_f2.readline()  # 去标题

    

    for line in in_f1:
        print(line, file=out_f)
        pass
    for line in in_f2:
        print(line, file=out_f)
        pass
    in_f1.close()
    in_f2.close()
    out_f.close()


if __name__ == "__main__":
    __main__()
    pass
