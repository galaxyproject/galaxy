/** SIF to JSON */
/** Inspired from https://www.npmjs.com/package/sif.js */
define( [], function() {

    function SIFJS() {};

    var nodes = {}, links = {}, content = [];
    
    var _getNode = function( id ) {
        if(!nodes[id]) nodes[id] = {id: id};
        return nodes[id];
    };

    var _parse = function( line, i ) {
        line = (line.split('\t').length > 1) ? line.split('\t') : line.split(' ');
        if( line.length && line.length > 0 && line[0] !== "" ) {
            var source = _getNode( line[0] ), intType = ( line[1] ? line[1] : "" ), j, length;
            if( intType !== "" ) {
                for (j = 2, length = line.length; j < length; j++) {
                    if( line[j] !== "" ) {
                        var target = _getNode(line[j]),
                        relObj = {target: target.id,
                            source: source.id,
                            id: source.id + target.id,
                            relation: intType.replace(/[''""]+/g, '') };
	                if(source < target) {
	                    links[ source.id + target.id + intType ] = relObj;
	                } else {
	                    links[ target.id + source.id + intType ] = relObj;
	                }
                    }	            
                }
            }
            else {
                links[ source.id ] = { target: "", source: source.id, id: source.id, relation: "" };
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
