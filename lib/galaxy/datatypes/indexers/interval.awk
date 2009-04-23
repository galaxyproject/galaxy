BEGIN {
    # from galaxy.utils
    mapped_chars[">"] = "__gt__"
    mapped_chars["<"] = "__lt__"
    mapped_chars["'"] = "__sq__"
    mapped_chars["\""] = "__dq__"
    mapped_chars["\\["] = "__ob__"
    mapped_chars["\\]"] = "__cb__"
    mapped_chars["\\{"] = "__oc__"
    mapped_chars["\\}"] = "__cc__"
    mapped_chars["@"] = "__at__"
    # additional, not in galaxy.utils
    mapped_chars["/"] = "__fs__"
    mapped_chars["^manifest\.tab$"] = "__manifest.tab__"
}
function escape_filename( name )
{
    for( char in mapped_chars ) {
	gsub( char, mapped_chars[char], name )
    }
    return name
}
!_[$chrom]++ {
    # close files only when we switch to a new one.
    fn && close(fn)
    fn = storepath "/" escape_filename($1) }
{   
    print $0 >> fn;
    # the || part is needed to catch 0 length chromosomes, which
    # should never happen but...
    if ($end > chroms[$chrom] || !chroms[$chrom])
	chroms[$chrom] = $end }
END { 
    fn = storepath "/manifest.tab"
    for( x in chroms ) {
	# add line to manifest
	print x "\t" chroms[x] >> fn
	chromfile = storepath "/" escape_filename(x)
	# sort in-place
	system( "sort -f -n -k " chrom " -k " start " -k " end " -o " chromfile " " chromfile )
	close(chromfile)
    }
}