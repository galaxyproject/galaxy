inf = file('hapmapQCtest.ped','r')
outf = file('hapmapQCtest.pednew','w')
for l in inf:
   ll = l.split()
   if len(ll) > 6:
      if int(ll[0]) < 1000: # yri
         ll[5]='2'
         print ll[:5],'touched'
      for i in range(6,len(ll)):
          if ll[i] == 'N':
            ll[i] = '0'
      outf.write(' '.join(ll))
      outf.write('\n')
outf.write('\n')
outf.close()
inf.close()

