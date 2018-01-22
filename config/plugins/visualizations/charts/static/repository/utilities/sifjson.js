/** Convert SIF files to JSON in a format required by Cytoscape
    for rendering the graph */
/** Inspired from https://www.npmjs.com/package/sif.js */
define( [], function() {

    function SIFJS() {};

    // Private variables and methods
    var nodes = {}, links = {}, content = [];
    
    // Add a node
    var _getNode = function( id ) {
        if(!nodes[id]) {
            nodes[id] = {id: id};
        }
        return nodes[id];
    };

    // Parse each line of the SIF file
    var _parse = function( line, i ) {
        var source, interaction, j, length;
        line = ( line.split('\t').length > 1 ) ? line.split('\t') : line.split(' ');
        source = _getNode( line[0] );
        interaction = ( line[1] ? line[1] : "" );
        if( line.length && line.length > 0 && line[0] !== "" ) {
            if( interaction !== "" ) {
                // Get all the target nodes for a source
                for ( j = 2, length = line.length; j < length; j++ ) {
                    if( line[j] !== "" ) {
                        // Create an object for each target for the source
                        var target = _getNode( line[j] ),
                        relation_object = {target: target.id,
                            source: source.id,
                            id: source.id + target.id,
                            relation: interaction.replace(/[''""]+/g, '') }; // Replace quotes in relation
                        if( source < target ) {
                            links[ source.id + target.id + interaction ] = relation_object;
                        } else {
                            links[ target.id + source.id + interaction ] = relation_object;
                        }
                    }
                }
            }
            // Handle the case of single node i.e. no relation with any other node
            // and only the source exists
            else {
                links[ source.id ] = { target: "", source: source.id, id: source.id, relation: "" };
            }
        }
    };

    // Convert to array from objects
    var _toArr = function( obj ) {
        var arr = [];
        for (var key in obj) {
            arr.push( obj[key] );
        }
        return arr;
    };

    // Make content from list of nodes and links
    var _toDataArr = function( nodes, links ) {
        var content = [], node_length, links_length;
        // Make a list of all nodes
        for(var i = 0, node_length = nodes.length; i < node_length; i++) {
            content.push( { 'data': nodes[i] } );
        }
        // Make a list of all relationships among nodes
        for(var i = 0, links_length = links.length; i < links_length; i++) {
            content.push( { 'data': links[i] } );
        }
        return content;
    };

    // Public method. Return graph data as JSON
    SIFJS.parse = function( text ) {
        var lines = text.split('\n'), i, length, nodesarr, linksarr;
        for ( i = 0, length = lines.length; i < length; i++ ) {
            if( lines[i] !== "" ) {
                _parse( lines[i], i );
            }
        }
        nodesarr = _toArr( nodes );
        linksarr = _toArr( links );
        return { content: _toDataArr( nodesarr, linksarr ) };
    };

    return {
        SIFJS     : SIFJS
    };
});
