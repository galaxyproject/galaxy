/** SIF to JSON */
define( [], function() {

    //public
    function SIFJS() {};

    //private members
    var nodes = {}, links = {}, content = [];
    
    var _getNode = function(id) {
        if(!nodes[id]) nodes[id] = {id:id};
        return nodes[id];
    };

    var _parse = function(line, i) {
        line = (line.split('\t').length > 1) ? line.split('\t') : line.split(' ');
        if( line.length > 2 ) {
            var source = _getNode(line[0]), intType = line[1], j, length;
            for (j = 2, length = line.length; j < length; j++) {
	        var target = _getNode(line[j]);
	        if(source < target){
	            links[source.id + target.id + intType] = {target: target.id, source: source.id, id: source.id + target.id};
	        } else {
	            links[target.id + source.id + intType] = {target: target.id, source: source.id, id: source.id + target.id};
	        }
            }
        }      
    };

    var _toArr = function( obj ) {
        var arr = [];
        for (var key in obj) arr.push( obj[key] );
        return arr;
    };

    var _toDataArr = function( nodes, links ) {
        var content = [];
        for(var i = 0; i < nodes.length; i++) content.push( { 'data': nodes[i] } );
        for(var i = 0; i < links.length; i++) content.push( { 'data': links[i] } );
        return content;
    };

    SIFJS.parse = function( text ) {
        var lines = text.split('\n'), i, length, nodesarr, linksarr;
        for ( i = 0, length = lines.length; i < length; i++ ) _parse(lines[i], i);
        nodesarr = _toArr(nodes);
        linksarr = _toArr(links);
        return {nodes: nodesarr, links: linksarr, content: _toDataArr( nodesarr, linksarr ) };
    };

    return {
        SIFJS     : SIFJS
    };
});
