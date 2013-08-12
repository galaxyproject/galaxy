# generate crap
import random,sys

part1list = ['pre','post','mid','sub','happy','cardio','glib','funk','']
part2list = ['mid','bar','nay','cluck','moo','self','half','jam','']
part3list = ['vol','temp','size','stage','vol','grade','race','']

def colname():
    """
    """
    part1 = random.choice(part1list)
    part2 = random.choice(part2list)
    part3 = random.choice(part3list)
    return '_'.join([part1,part2,part3])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print '## error - need ncols, nrows and outfilepath please'
        sys.exit(1)    
    c = int(sys.argv[1])
    r = int(sys.argv[2])
    o = sys.argv[3]
    outf = open(o,'w')
    cols = [colname() for x in range(c)]
    outf.write('\t'.join(cols))
    for row in range(r):
        print 'row',row
        outf.write('\t'.join(['%f' % random.random() for x in range(c)]))
        outf.write('\n')
    outf.close()

