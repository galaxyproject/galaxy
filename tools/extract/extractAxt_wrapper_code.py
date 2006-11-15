# Load the list of available alignments when the tool is initialized
aligndb = dict()
for line in open( "/depot/data2/galaxy/alignseq.loc" ):
    fields = line.split()
    if fields[0] == "align":
        try: aligndb[fields[1]].append( fields[2] )
        except: aligndb[fields[1]] = [ fields[2] ]

def get_available_alignments_for_build( build ):
    # FIXME: We need a database of descriptive names corresponding to dbkeys.
    #        We need to resolve the musMusX <--> mmX confusion
    rval = []
    if build[0:2] == "mm":
        build = build.replace('mm','musMus')
    if build[0:2] == "rn":
        build = build.replace('rn','ratNor')
    if build in aligndb:
        for val in aligndb[build]:
            rval.append( ( val, val, False ) )
    return rval        
