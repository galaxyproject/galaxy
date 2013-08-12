# make individual chromosome, offspring/founder/all files for each race
# kludge fix for 4 allele x chromosome snp rs3810755
# some strangeness in the data as at october 2007
# like the illumina 550k data
# looks like lots of missings for non ceu
# added some counters..
# added routine to generate a test data set for
# the infinium pipeline with real hapmap family data
# yri + ceu families - 60 trios with as many infinium 550k snps
# modified august 22 2007 to make a file containing
# all hapmap samples into ped files with the 550k snp genotypes
# for eigenstrat seeding
# ross lazarus 22 august 2007


import time, sys, os, random, copy, array

import MySQLdb

try:
    import psyco
    psyco.full()
except:
    print 'no psyco :('
debug = 1




hapmapped = {'NA18564': ['22', '22', '0', '0', '2', '1'], 'NA18987': ['78', '258', '0', '0', '2', '1'],
             'NA18566': ['23', '23', '0', '0', '2', '1'], 'NA10835': ['1416', '1', '11', '12', '1', '1'],
             'NA18561': ['6', '6', '0', '0', '1', '1'], 'NA18562': ['7', '7', '0', '0', '1', '1'],
             'NA18563': ['24', '24', '0', '0', '1', '1'], 'NA07357': ['1345', '12', '0', '0', '1', '1'],
             'NA10838': ['1420', '1', '9', '10', '1', '1'], 'NA10839': ['1420', '2', '11', '12', '2', '1'],
             'NA11831': ['1350', '12', '0', '0', '1', '1'], 'NA11830': ['1350', '11', '0', '0', '2', '1'],
             'NA07056': ['1340', '12', '0', '0', '2', '1'], 'NA11832': ['1350', '13', '0', '0', '2', '1'],
             'NA12056': ['1344', '12', '0', '0', '1', '1'], 'NA12057': ['1344', '13', '0', '0', '2', '1'],
             'NA18863': ['24', '1', '3', '2', '1', '1'], 'NA18862': ['24', '3', '0', '0', '1', '1'],
             'NA11839': ['1349', '13', '0', '0', '1', '1'], 'NA18967': ['69', '249', '0', '0', '1', '1'],
             'NA19130': ['101', '3', '0', '0', '1', '1'], 'NA10830': ['1408', '1', '10', '11', '1', '1'],
             'NA10831': ['1408', '2', '12', '13', '2', '1'], 'NA12264': ['1375', '11', '0', '0', '1', '1'],
             'NA18516': ['13', '3', '0', '0', '1', '1'], 'NA12707': ['1358', '1', '11', '12', '1', '1'],
             'NA18968': ['59', '239', '0', '0', '2', '1'], 'NA19116': ['60', '2', '0', '0', '2', '1'],
             'NA18550': ['17', '17', '0', '0', '2', '1'], 'NA18552': ['19', '19', '0', '0', '2', '1'],
             'NA07348': ['1345', '2', '12', '13', '2', '1'], 'NA10846': ['1334', '1', '10', '11', '1', '1'],
             'NA19192': ['112', '3', '0', '0', '1', '1'], 'NA18558': ['4', '4', '0', '0', '1', '1'],
             'NA19137': ['43', '2', '0', '0', '2', '1'], 'NA19171': ['47', '3', '0', '0', '1', '1'],
             'NA19172': ['47', '2', '0', '0', '2', '1'], 'NA19173': ['47', '1', '3', '2', '1', '1'],
             'NA18872': ['17', '1', '3', '2', '1', '1'], 'NA19138': ['43', '3', '0', '0', '1', '1'],
             'NA18870': ['17', '2', '0', '0', '2', '1'], 'NA18871': ['17', '3', '0', '0', '1', '1'],
             'NA19161': ['56', '1', '3', '2', '1', '1'], 'NA11829': ['1350', '10', '0', '0', '1', '1'],
             'NA19160': ['56', '3', '0', '0', '1', '1'], 'NA06985': ['1341', '14', '0', '0', '2', '1'],
             'NA19132': ['101', '1', '3', '2', '2', '1'], 'NA18978': ['71', '251', '0', '0', '2', '1'],
             'NA07055': ['1341', '12', '0', '0', '2', '1'], 'NA18973': ['66', '246', '0', '0', '2', '1'],
             'NA18972': ['64', '244', '0', '0', '2', '1'], 'NA18981': ['75', '255', '0', '0', '2', '1'],
             'NA18970': ['72', '252', '0', '0', '1', '1'], 'NA18976': ['70', '250', '0', '0', '2', '1'],
             'NA18975': ['68', '248', '0', '0', '2', '1'], 'NA18974': ['77', '257', '0', '0', '1', '1'],
             'NA19206': ['51', '2', '0', '0', '2', '1'], 'NA19207': ['51', '3', '0', '0', '1', '1'],
             'NA19204': ['48', '2', '0', '0', '2', '1'], 'NA19205': ['48', '1', '3', '2', '1', '1'],
             'NA19202': ['45', '1', '3', '2', '2', '1'], 'NA19203': ['48', '3', '0', '0', '1', '1'],
             'NA19200': ['45', '3', '0', '0', '1', '1'], 'NA19201': ['45', '2', '0', '0', '2', '1'],
             'NA18861': ['24', '2', '0', '0', '2', '1'], 'NA18960': ['62', '242', '0', '0', '1', '1'],
             'NA18971': ['76', '256', '0', '0', '1', '1'], 'NA19208': ['51', '1', '3', '2', '1', '1'],
             'NA18860': ['12', '1', '3', '2', '1', '1'], 'NA10851': ['1344', '1', '12', '13', '1', '1'],
             'NA06994': ['1340', '9', '0', '0', '1', '1'], 'NA10854': ['1349', '2', '13', '14', '2', '1'],
             'NA10855': ['1350', '2', '12', '13', '2', '1'], 'NA10856': ['1350', '1', '10', '11', '1', '1'],
             'NA10857': ['1346', '1', '11', '12', '1', '1'], 'NA12801': ['1454', '1', '12', '13', '1', '1'],
             'NA18547': ['15', '15', '0', '0', '2', '1'], 'NA19143': ['74', '2', '0', '0', '2', '1'],
             'NA18545': ['13', '13', '0', '0', '2', '1'], 'NA18542': ['12', '12', '0', '0', '2', '1'],
             'NA19144': ['74', '3', '0', '0', '1', '1'], 'NA18540': ['10', '10', '0', '0', '2', '1'],
             'NA18980': ['73', '253', '0', '0', '2', '1'], 'NA18953': ['58', '238', '0', '0', '1', '1'],
             'NA18969': ['61', '241', '0', '0', '2', '1'], 'NA19194': ['112', '1', '3', '2', '1', '1'],
             'NA19209': ['50', '2', '0', '0', '2', '1'], 'NA18961': ['63', '243', '0', '0', '1', '1'],
             'NA18964': ['57', '237', '0', '0', '2', '1'], 'NA19240': ['117', '1', '3', '2', '2', '1'],
             'NA18966': ['67', '247', '0', '0', '1', '1'], 'NA18517': ['13', '2', '0', '0', '2', '1'],
             'NA12760': ['1447', '9', '0', '0', '1', '1'], 'NA12761': ['1447', '10', '0', '0', '2', '1'],
             'NA12762': ['1447', '11', '0', '0', '1', '1'], 'NA12763': ['1447', '12', '0', '0', '2', '1'],
             'NA18952': ['55', '235', '0', '0', '1', '1'], 'NA19005': ['86', '266', '0', '0', '1', '1'],
             'NA19007': ['88', '268', '0', '0', '1', '1'], 'NA19000': ['85', '265', '0', '0', '1', '1'],
             'NA19003': ['89', '269', '0', '0', '2', '1'], 'NA19140': ['71', '2', '0', '0', '2', '1'],
             'NA18532': ['5', '5', '0', '0', '2', '1'], 'NA18537': ['8', '8', '0', '0', '2', '1'],
             'NA10860': ['1362', '1', '13', '14', '1', '1'], 'NA10863': ['1375', '2', '11', '12', '2', '1'],
             'NA11992': ['1362', '13', '0', '0', '1', '1'], 'NA11993': ['1362', '14', '0', '0', '2', '1'],
             'NA18956': ['56', '236', '0', '0', '2', '1'], 'NA18951': ['48', '228', '0', '0', '2', '1'],
             'NA11882': ['1347', '15', '0', '0', '2', '1'], 'NA11994': ['1362', '15', '0', '0', '1', '1'],
             'NA11995': ['1362', '16', '0', '0', '2', '1'], 'NA11840': ['1349', '14', '0', '0', '2', '1'],
             'NA07000': ['1340', '10', '0', '0', '2', '1'], 'NA12892': ['1463', '16', '0', '0', '2', '1'],
             'NA19129': ['77', '1', '3', '2', '2', '1'], 'NA19193': ['112', '2', '0', '0', '2', '1'],
             'NA12891': ['1463', '15', '0', '0', '1', '1'], 'NA12003': ['1420', '9', '0', '0', '1', '1'],
             'NA19128': ['77', '3', '0', '0', '1', '1'], 'NA12005': ['1420', '11', '0', '0', '1', '1'],
             'NA12004': ['1420', '10', '0', '0', '2', '1'], 'NA12753': ['1447', '2', '11', '12', '2', '1'],
             'NA12006': ['1420', '12', '0', '0', '2', '1'], 'NA19099': ['105', '2', '0', '0', '2', '1'],
             'NA19098': ['105', '3', '0', '0', '1', '1'], 'NA19152': ['72', '2', '0', '0', '2', '1'],
             'NA18624': ['36', '36', '0', '0', '1', '1'], 'NA18623': ['33', '33', '0', '0', '1', '1'],
             'NA18622': ['31', '31', '0', '0', '1', '1'], 'NA18621': ['29', '29', '0', '0', '1', '1'],
             'NA18620': ['28', '28', '0', '0', '1', '1'], 'NA18529': ['3', '3', '0', '0', '2', '1'],
             'NA19142': ['71', '1', '3', '2', '1', '1'], 'NA19153': ['72', '3', '0', '0', '1', '1'],
             'NA18521': ['16', '1', '3', '2', '1', '1'], 'NA18522': ['16', '3', '0', '0', '1', '1'],
             'NA18523': ['16', '2', '0', '0', '2', '1'], 'NA18524': ['2', '2', '0', '0', '1', '1'],
             'NA18526': ['1', '1', '0', '0', '2', '1'], 'NA18942': ['46', '226', '0', '0', '2', '1'],
             'NA07019': ['1340', '2', '11', '12', '2', '1'], 'NA18940': ['47', '227', '0', '0', '1', '1'],
             'NA18947': ['50', '230', '0', '0', '2', '1'], 'NA18944': ['51', '231', '0', '0', '1', '1'],
             'NA18945': ['52', '232', '0', '0', '1', '1'], 'NA19119': ['60', '3', '0', '0', '1', '1'],
             'NA18948': ['54', '234', '0', '0', '1', '1'], 'NA18949': ['53', '233', '0', '0', '2', '1'],
             'NA06993': ['1341', '13', '0', '0', '1', '1'], 'NA18965': ['65', '245', '0', '0', '1', '1'],
             'NA12156': ['1408', '13', '0', '0', '2', '1'], 'NA12155': ['1408', '12', '0', '0', '1', '1'],
             'NA12154': ['1408', '10', '0', '0', '1', '1'], 'NA18959': ['60', '240', '0', '0', '1', '1'],
             'NA06991': ['1341', '2', '13', '14', '2', '1'], 'NA19154': ['72', '1', '3', '2', '1', '1'],
             'NA19012': ['90', '270', '0', '0', '1', '1'], 'NA19141': ['71', '3', '0', '0', '1', '1'],
             'NA12814': ['1454', '14', '0', '0', '1', '1'], 'NA12815': ['1454', '15', '0', '0', '2', '1'],
             'NA12812': ['1454', '12', '0', '0', '1', '1'], 'NA12813': ['1454', '13', '0', '0', '2', '1'],
             'NA10859': ['1347', '2', '14', '15', '2', '1'], 'NA18635': ['41', '41', '0', '0', '1', '1'],
             'NA18636': ['43', '43', '0', '0', '1', '1'], 'NA18637': ['45', '45', '0', '0', '1', '1'],
             'NA18632': ['38', '38', '0', '0', '1', '1'], 'NA18633': ['40', '40', '0', '0', '1', '1'],
             'NA12802': ['1454', '2', '14', '15', '2', '1'], 'NA19239': ['117', '3', '0', '0', '1', '1'],
             'NA07022': ['1340', '11', '0', '0', '1', '1'], 'NA19145': ['74', '1', '3', '2', '1', '1'],
             'NA07029': ['1340', '1', '9', '10', '1', '1'], 'NA12239': ['1334', '13', '0', '0', '2', '1'],
             'NA12751': ['1444', '14', '0', '0', '2', '1'], 'NA12236': ['1408', '11', '0', '0', '2', '1'],
             'NA12234': ['1375', '12', '0', '0', '2', '1'], 'NA12750': ['1444', '13', '0', '0', '1', '1'],
             'NA12144': ['1334', '10', '0', '0', '1', '1'], 'NA12145': ['1334', '11', '0', '0', '2', '1'],
             'NA12146': ['1334', '12', '0', '0', '1', '1'], 'NA12752': ['1447', '1', '9', '10', '1', '1'],
             'NA18609': ['16', '16', '0', '0', '1', '1'], 'NA18608': ['18', '18', '0', '0', '1', '1'],
             'NA19120': ['60', '1', '3', '2', '1', '1'], 'NA19127': ['77', '2', '0', '0', '2', '1'],
             'NA12865': ['1459', '2', '11', '12', '2', '1'], 'NA12864': ['1459', '1', '9', '10', '1', '1'],
             'NA18603': ['9', '9', '0', '0', '1', '1'], 'NA19159': ['56', '2', '0', '0', '2', '1'],
             'NA18605': ['11', '11', '0', '0', '1', '1'], 'NA18853': ['18', '3', '0', '0', '1', '1'],
             'NA07034': ['1341', '11', '0', '0', '1', '1'], 'NA19221': ['58', '1', '3', '2', '2', '1'],
             'NA19222': ['58', '2', '0', '0', '2', '1'], 'NA19223': ['58', '3', '0', '0', '1', '1'],
             'NA18505': ['5', '2', '0', '0', '2', '1'], 'NA19094': ['40', '1', '3', '2', '2', '1'],
             'NA18555': ['21', '21', '0', '0', '2', '1'], 'NA18943': ['49', '229', '0', '0', '1', '1'],
             'NA18612': ['26', '26', '0', '0', '1', '1'], 'NA12249': ['1416', '12', '0', '0', '2', '1'],
             'NA18611': ['20', '20', '0', '0', '1', '1'], 'NA18594': ['30', '30', '0', '0', '2', '1'],
             'NA19238': ['117', '2', '0', '0', '2', '1'], 'NA18593': ['44', '44', '0', '0', '2', '1'],
             'NA18592': ['42', '42', '0', '0', '2', '1'], 'NA18515': ['13', '1', '3', '2', '1', '1'],
             'NA19131': ['101', '2', '0', '0', '2', '1'], 'NA12872': ['1459', '9', '0', '0', '1', '1'],
             'NA12873': ['1459', '10', '0', '0', '2', '1'], 'NA12874': ['1459', '11', '0', '0', '1', '1'],
             'NA12875': ['1459', '12', '0', '0', '2', '1'], 'NA07345': ['1345', '13', '0', '0', '2', '1'],
             'NA12878': ['1463', '2', '15', '16', '2', '1'], 'NA19139': ['43', '1', '3', '2', '1', '1'],
             'NA18577': ['35', '35', '0', '0', '2', '1'], 'NA18576': ['34', '34', '0', '0', '2', '1'],
             'NA18573': ['32', '32', '0', '0', '2', '1'], 'NA18572': ['14', '14', '0', '0', '1', '1'],
             'NA18571': ['27', '27', '0', '0', '2', '1'], 'NA18570': ['25', '25', '0', '0', '2', '1'],
             'NA19211': ['50', '1', '3', '2', '1', '1'], 'NA19210': ['50', '3', '0', '0', '1', '1'],
             'NA12740': ['1444', '2', '13', '14', '2', '1'], 'NA11881': ['1347', '14', '0', '0', '1', '1'],
             'NA18579': ['37', '37', '0', '0', '2', '1'], 'NA10847': ['1334', '2', '12', '13', '2', '1'],
             'NA18999': ['87', '267', '0', '0', '2', '1'], 'NA12044': ['1346', '12', '0', '0', '2', '1'],
             'NA19092': ['40', '3', '0', '0', '1', '1'], 'NA10861': ['1362', '2', '15', '16', '2', '1'],
             'NA12043': ['1346', '11', '0', '0', '1', '1'], 'NA18991': ['80', '260', '0', '0', '2', '1'],
             'NA18990': ['79', '259', '0', '0', '1', '1'], 'NA18992': ['82', '262', '0', '0', '2', '1'],
             'NA18995': ['74', '254', '0', '0', '1', '1'], 'NA18994': ['81', '261', '0', '0', '1', '1'],
             'NA18997': ['83', '263', '0', '0', '2', '1'], 'NA07048': ['1341', '1', '11', '12', '1', '1'],
             'NA18858': ['12', '2', '0', '0', '2', '1'], 'NA18859': ['12', '3', '0', '0', '1', '1'],
             'NA18913': ['28', '3', '0', '0', '1', '1'], 'NA18912': ['28', '2', '0', '0', '2', '1'],
             'NA18914': ['28', '1', '3', '2', '1', '1'], 'NA18504': ['5', '3', '0', '0', '1', '1'],
             'NA18582': ['39', '39', '0', '0', '2', '1'], 'NA19093': ['40', '2', '0', '0', '2', '1'],
             'NA18852': ['18', '2', '0', '0', '2', '1'], 'NA12248': ['1416', '11', '0', '0', '1', '1'],
             'NA18854': ['18', '1', '3', '2', '1', '1'], 'NA18855': ['23', '2', '0', '0', '2', '1'],
             'NA18856': ['23', '3', '0', '0', '1', '1'], 'NA18857': ['23', '1', '3', '2', '1', '1'],
             'NA18502': ['4', '2', '0', '0', '2', '1'], 'NA18503': ['5', '1', '3', '2', '1', '1'],
             'NA18500': ['4', '1', '3', '2', '1', '1'], 'NA18501': ['4', '3', '0', '0', '1', '1'],
             'NA18506': ['9', '1', '3', '2', '1', '1'], 'NA18507': ['9', '3', '0', '0', '1', '1'],
             'NA12717': ['1358', '12', '0', '0', '2', '1'], 'NA12716': ['1358', '11', '0', '0', '1', '1'],
             'NA18998': ['84', '264', '0', '0', '2', '1'], 'NA18508': ['9', '2', '0', '0', '2', '1'],
             'NA19101': ['42', '3', '0', '0', '1', '1'], 'NA19100': ['105', '1', '3', '2', '2', '1'],
             'NA19103': ['42', '1', '3', '2', '1', '1'], 'NA19102': ['42', '2', '0', '0', '2', '1']}

adict = {'A':'1','C':'2','G':'3','T':'4','N':'0','0':'0',
         '1':'1','2':'2','3':'3','4':'4'} # acgtn12340 all should work


def writeFO(chrom=None,idgeno = {}, thismap=[], race='CEU', source="hm550k",ignoreme={}):
    """write everyone, then if there are offspring, founders and offspring separately
    """
    allres = []
    fres = []
    ores = []
    thismap.sort() # chrom,pos,rs
    rslist = [x[2] for x in thismap if not ignoreme.get(x[2],None)]
    print 'WriteFO chrom=%s, race=%s, thismap=%s' % (chrom,race,thismap[:10])
    mres = ['%s\t%s\t0\t%d' % (x[0],x[2],x[1]) for x in thismap if not ignoreme.get(x[2],None)] # thismap.append((chrom,int(pos),rs))
    # split everyone
    if race <> None: # an individual race/chromosome file
         for id in idgeno.keys(): # for each subject
            row = copy.copy(hapmapped[id]) # want founders only
            ma,pa = row[2:4]
            row += [idgeno[id].get(rs,'0 0') for rs in rslist] # all snps in order or missing
            s = ' '.join(row)
            if (ma == '0' and pa == '0'): # founder
               fres.append(s)
            else:
                ores.append(s)
            allres.append(s)
    else:
        race = 'ALL'
        for r in idgeno.keys(): # keyed by race if doing all
            for id in idgeno[r].keys(): # for each subject
                row = copy.copy(hapmapped[id]) # want founders only
                ma,pa = row[2:4]
                row += [idgeno[r][id].get(rs,'0 0') for rs in rslist] # all snps in order or missing
                s = ' '.join(row)
                if (ma == '0' and pa == '0'): # founder
                   fres.append(s)
                else:
                    ores.append(s)
                allres.append(s)
    allres.sort()
    if chrom <> None:
        fname = '%s_chr%s_%s' % (source,chrom,race)
    else:
        fname = '%s_%s' % (source,race)
    outf = file('%s.ped' % fname,'w')
    outf.write('%s\n' % '\n'.join(allres)) # add newline to last row!
    outf.close()
    outf = file('%s.map' % fname,'w')
    outf.write('%s\n' % '\n'.join(mres)) # add newline to last row!
    outf.close()
    print 'wrote %d rows to %s.ped' % (len(allres),fname)
    if len(ores) > 0: # write founder and offspring separately for CEU and YRI
        fres.sort()
        if chrom <> None:
            fname = '%s_chr%s_%s_%s' % (source,chrom,race,'founders')
        else:
            fname = '%s_%s_%s' % (source,race,'founders')
        outf = file('%s.ped' % fname,'w')
        outf.write('%s\n' % '\n'.join(fres)) # add newline to last row!
        outf.close()        
        outf = file('%s.map' % fname,'w')
        outf.write('%s\n' % '\n'.join(mres)) # add newline to last row!
        if chrom <> None:
            fname = '%s_chr%s_%s_%s' % (source,chrom,race,'offspring')
        else:
            fname = '%s_%s_%s' % (source,race,'offspring')
        ores.sort()
        outf = file('%s.ped' % fname,'w')
        outf.write('%s\n' % '\n'.join(ores)) # add newline to last row!
        outf.close()        
        outf = file('%s.map' % fname,'w')
        outf.write('%s\n' % '\n'.join(mres)) # add newline to last row!
        outf.close()
    

def writeHapMap(testing = 1,  chrlist = [],  runname=None, source="hm550k"):
    """write a hapmap ped file with all affected offspring (!)
    for plink testing
    ross lazarus march 8 2007
    """
    ignoreme = {} # some > 2 allele snps
    rsadict = {}
    racelist=['CEU','CHB','JPT','YRI']
    genome = MySQLdb.Connect('hg', 'refseq', 'Genbank')
    #genome = MySQLdb.Connect(host='localhost', user='refseq', passwd='Genbank', port=3307)
    curs = genome.cursor(cursorclass=MySQLdb.cursors.DictCursor) # use dict cursor as cols are subject ids
    lcurs = genome.cursor() # use ordinary cursor for amap
    if chrlist == []: # make a full one
       chrlist = map(str,range(1,23))
       chrlist += ['X','Y']
    if testing and (len(chrlist) > 2):
       chrlist= chrlist[-2:]
    chrmaplist = {}
    allmaplist = []
    nmissbyrace = {}
    for race in racelist:
       nmissbyrace[race] = 0
    if runname == None:
        runname = '%s_550k' % '_'.join(racelist)
    for chrom in chrlist: # work by chrom as hapmap data is organized that way
        print 'getting %s' % chrom
        chrmaplist[chrom] = []
        lcurs.execute('select chrom,rs,offset from HumanHap550.HumanHap550v3_A where chrom="%s" order by offset' % (chrom))
        amap = lcurs.fetchall()
        amap = [(x[0],int(x[2]),x[1]) for x in amap] # thismap.append((chrom,int(pos),rs))
        allmaplist += amap
        chrmaplist[chrom] = amap
    print 'allmaplist=%s' % (allmaplist[:10])
    print 'Got all 550kv3 markers'
    subjgeno = {}
    for racenum,race in enumerate(racelist):
        nrs = 0
        subjgeno[race] = {}
        print 'race=',race
        for chrom in chrlist: # work by chrom as hapmap data is organized that way
            thischrom = {}
            thismap = []
            print 'chrom=',chrom,'in',chrlist
            curs.execute('''select * from hapmap.%s_%s where RS in
            (select rs from HumanHap550.HumanHap550v3_A where chrom="%s" order by offset)''' % (race,chrom,chrom))
            for hmap in curs.fetchall():
                rs = hmap['RS']
                pos = hmap['POS']
                nrs += 1
                if nrs % 10000 == 0:
                   print '%s at %d, rs %s, nmiss = %d' % (race,nrs,rs,nmissbyrace[race])
                for k in hmap.keys(): # identifiers are used to store genotypes (!)
                    if k[:2] == 'NA': # is a NA identifier field
                        geno = map(None,hmap[k]) # to list
                        geno = [adict.get(x,'0') for x in geno]
                        if not rsadict.get(rs,None):
                            rsadict[rs] = {}
                        for g in geno:
                            if g <> '0':
                                if rsadict[rs].get(g,None):
                                    rsadict[rs][g] += 1
                                else:
                                    rsadict[rs][g] = 1
                        if len(rsadict[rs].keys()) > 2:
			    if ignoreme.get(rs,None):
	                            print '###for rs %s, race %s, chrom %s we now have %s' % (rs,race,chrom,rsadict[rs])
        	                    ignoreme[rs] = rs # set to not output this rs
                        if len(geno) <> 2:
                            print 'strange geno',geno
                        else:
                            sg = '%s %s' % (geno[0],geno[1]) # genotype
                            if subjgeno[race].get(k,None):
                                subjgeno[race][k][rs] = sg
                            else: # first time
                                subjgeno[race][k] = {rs:sg,}
                        if sg[0] == '0' or sg[2] == '0': # missing
                             nmissbyrace[race] += 1 
            # write out thischrom results (founders and offspring..)
            writeFO(chrom,subjgeno[race],chrmaplist[chrom],race,source,ignoreme)
            print 'for race %s chrom %s found %d rs with %d missing' % (race, chrom, nrs, nmissbyrace[race])
        # now have all race subjects in subjgeno
        writeFO(None, subjgeno[race], allmaplist, race, source,ignoreme) 
        #each race
    writeFO(None,subjgeno,allmaplist,None,source,ignoreme) # all
    print 'summary of missings -',str(nmissbyrace)




    
if __name__ == "__main__":

    # first time only
    #makeIll()
    #writeCEU_YRI(testing = 0, ftest = 0.1, chrlist = [22], offspringToo = 0, runname='CEU_YRI_chr22_Founders')
    writeHapMap(testing = 0, chrlist = [], runname='hmCEU_all')
