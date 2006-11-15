scores = {}
for line in open( '/cache/phastOdds_precomputed/index.txt' ):
    fields = line.strip().split( "\t" )
    if not fields[0] in scores: scores[fields[0]] = []
    scores[ fields[0] ].append( (fields[1],fields[2]) )

def get_scores_for_build( build ):
    rval = []
    if build in scores:
        for (descript,scorefile) in scores[build]:
            rval.append( (descript,scorefile, False) )
    return rval        
