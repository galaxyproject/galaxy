cimport cython
from libc.stdlib cimport malloc, free

cimport cedlib

def align(query, target, mode="NW", task="distance", k=-1, additionalEqualities=None):
    """ Align query with target using edit distance.
    @param {string} query
    @param {string} target
    @param {string} mode  Optional. Alignment method do be used. Possible values are:
            - 'NW' for global (default)
            - 'HW' for infix
            - 'SHW' for prefix.
    @param {string} task  Optional. Tells edlib what to calculate. Less there is to calculate,
            faster it is. Possible value are (from fastest to slowest):
            - 'distance' - find edit distance and end locations in target. Default.
            - 'locations' - find edit distance, end locations and start locations.
            - 'path' - find edit distance, start and end locations and alignment path.
    @param {int} k  Optional. Max edit distance to search for - the lower this value,
            the faster is calculation. Set to -1 (default) to have no limit on edit distance.
    @param {list} additionalEqualities  Optional.
            List of pairs of characters, where each pair defines two characters as equal.
            This way you can extend edlib's definition of equality (which is that each character is equal only
            to itself).
            This can be useful e.g. when you want edlib to be case insensitive, or if you want certain
            characters to act as a wildcards.
            Set to None (default) if you do not want to extend edlib's default equality definition.
    @return Dictionary with following fields:
            {int} editDistance  -1 if it is larger than k.
            {int} alphabetLength
            {[(int, int)]} locations  List of locations, in format [(start, end)].
            {string} cigar  Cigar is a standard format for alignment path.
                Here we are using extended cigar format, which uses following symbols:
                Match: '=', Insertion to target: 'I', Deletion from target: 'D', Mismatch: 'X'.
                e.g. cigar of "5=1X1=1I" means "5 matches, 1 mismatch, 1 match, 1 insertion (to target)".
    """
    # Transform python strings into c strings.
    cdef bytes query_bytes = query.encode();
    cdef char* cquery = query_bytes;
    cdef bytes target_bytes = target.encode();
    cdef char* ctarget = target_bytes;

    # Build an edlib config object based on given parameters.
    cconfig = cedlib.edlibDefaultAlignConfig()

    if k is not None: cconfig.k = k

    if mode == 'NW': cconfig.mode = cedlib.EDLIB_MODE_NW
    if mode == 'HW': cconfig.mode = cedlib.EDLIB_MODE_HW
    if mode == 'SHW': cconfig.mode = cedlib.EDLIB_MODE_SHW

    if task == 'distance': cconfig.task = cedlib.EDLIB_TASK_DISTANCE
    if task == 'locations': cconfig.task = cedlib.EDLIB_TASK_LOC
    if task == 'path': cconfig.task = cedlib.EDLIB_TASK_PATH

    cdef bytes tmp_bytes;
    cdef char* tmp_cstring;
    if additionalEqualities is None:
        cconfig.additionalEqualities = NULL
        cconfig.additionalEqualitiesLength = 0
    else:
        cconfig.additionalEqualities = <cedlib.EdlibEqualityPair*> malloc(len(additionalEqualities)
                                                                          * cython.sizeof(cedlib.EdlibEqualityPair))
        for i in range(len(additionalEqualities)):
            # TODO(martin): Is there a better way to do this conversion? There must be.
            tmp_bytes = additionalEqualities[i][0].encode();
            tmp_cstring = tmp_bytes;
            cconfig.additionalEqualities[i].first = tmp_cstring[0]
            tmp_bytes = additionalEqualities[i][1].encode();
            tmp_cstring = tmp_bytes;
            cconfig.additionalEqualities[i].second = tmp_cstring[0]
        cconfig.additionalEqualitiesLength = len(additionalEqualities)

    # Run alignment.
    cresult = cedlib.edlibAlign(cquery, len(query), ctarget, len(target), cconfig)
    if cconfig.additionalEqualities != NULL: free(cconfig.additionalEqualities)

    if cresult.status == 1:
        raise Exception("There was an error.")

    # Build python dictionary with results from result object that edlib returned.
    locations = []
    if cresult.numLocations >= 0:
        for i in range(cresult.numLocations):
            locations.append((cresult.startLocations[i] if cresult.startLocations else None,
                              cresult.endLocations[i] if cresult.endLocations else None))
    cigar = None
    if cresult.alignment:
        ccigar = cedlib.edlibAlignmentToCigar(cresult.alignment, cresult.alignmentLength,
                                              cedlib.EDLIB_CIGAR_EXTENDED)
        cigar = <bytes> ccigar
        cigar = cigar.decode('UTF-8')
    result = {
        'editDistance': cresult.editDistance,
        'alphabetLength': cresult.alphabetLength,
        'locations': locations,
        'cigar': cigar
    }
    cedlib.edlibFreeAlignResult(cresult)

    return result
