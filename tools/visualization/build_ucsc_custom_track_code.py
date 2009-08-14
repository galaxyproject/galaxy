# runs after the job (and after the default post-filter)

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

def validate_input( trans, error_map, param_values, page_param_map ):
    dbkeys = set()
    tracks = param_values['tracks']
    for track in tracks:
        if track['input']:
            dbkeys.add( track['input'].dbkey )
    if len( dbkeys ) > 1:
        # FIXME: Should be able to assume error map structure is created
        if 'tracks' not in error_map:
            error_map['tracks'] = [ dict() for t in tracks ]
            for i in range( len( tracks ) ):
                error_map['tracks'][i]['input'] = \
                    "All datasets must belong to same genomic build"