define([
],function(){
/* ============================================================================
TODO:
    edges can't retain data

============================================================================ */
//TODO: go ahead and move to underscore...
function each( d, fn ){
    for( var k in d ){
        if( d.hasOwnProperty( k ) ){
            fn( d[ k ], k, d );
        }
    }
}

function extend( d, d2 ){
    for( var k in d2 ){
        if( d2.hasOwnProperty( k ) ){
            d[ k ] = d2[ k ];
        }
    }
    return d;
}

function matches( d, d2 ){
    for( var k in d2 ){
        if( d2.hasOwnProperty( k ) ){
            if( !d.hasOwnProperty( k ) || d[ k ] !== d2[ k ] ){
                return false;
            }
        }
    }
    return true;
}

function iterate( obj, propsOrFn ){
    var fn =    typeof propsOrFn === 'function'? propsOrFn : undefined,
        props = typeof propsOrFn === 'object'?   propsOrFn : undefined,
        returned = [],
        index = 0;
    for( var key in obj ){
        if( obj.hasOwnProperty( key ) ){
            var value = obj[ key ];
            if( fn ){
                returned.push( fn.call( value, value, key, index ) );
            } else if( props ){
//TODO: break out to sep?
                if( typeof value === 'object' && matches( value, props ) ){
                    returned.push( value );
                }
            } else {
                returned.push( value );
            }
            index += 1;
        }
    }
    return returned;
}


// ============================================================================
function Edge( source, target, data ){
    var self = this;
    self.source = source !== undefined? source : null;
    self.target = target !== undefined? target : null;
    self.data = data || null;
    //if( typeof data === 'object' ){
    //    extend( self, data );
    //}
    return self;
}
Edge.prototype.toString = function(){
    return this.source + '->' + this.target;
};

Edge.prototype.toJSON = function(){
    //TODO: this is safe in most browsers (fns will be stripped) - alter tests to incorporate this in order to pass data
    //return this;
    var json = {
        source : this.source,
        target : this.target
    };
    if( this.data ){
        json.data = this.data;
    }
    return json;
};

// ============================================================================
function Vertex( name, data ){
    var self = this;
    self.name = name !== undefined? name : '(unnamed)';
    self.data = data || null;
    self.edges = {};
    self.degree = 0;
    return self;
}
window.Vertex = Vertex;
Vertex.prototype.toString = function(){
    return 'Vertex(' + this.name + ')';
};

//TODO: better name w no collision for either this.eachEdge or this.edges
Vertex.prototype.eachEdge = function( propsOrFn ){
    return iterate( this.edges, propsOrFn );
};

Vertex.prototype.toJSON = function(){
    //return this;
    return {
        name : this.name,
        data : this.data
    };
};


// ============================================================================
var GraphSearch = function( graph, processFns ){
    var self = this;
    self.graph = graph;

    self.processFns = processFns || {
        vertexEarly : function( vertex, search ){
            //console.debug( 'processing vertex:', vertex.name, vertex );
        },
        edge        : function( from, edge, search ){
            //console.debug( this, 'edge:', from, edge, search );
        },
        vertexLate  : function( vertex, search ){
            //console.debug( this, 'vertexLate:', vertex, search );
        }
    };

    self._cache = {};
    return self;
};

GraphSearch.prototype.search = function _search( start ){
    var self = this;
    if( start in self._cache ){ return self._cache[ start ]; }
    if( !( start instanceof Vertex ) ){ start = self.graph.vertices[ start ]; }
    return ( self._cache[ start.name ] = self._search( start ) );
};

GraphSearch.prototype._searchTree = function __searchTree( search ){
    var self = this;
    return new Graph( true, {
        edges: search.edges,
        vertices: Object.keys( search.discovered ).map( function( key ){
            return self.graph.vertices[ key ].toJSON();
        })
    });
};

GraphSearch.prototype.searchTree = function _searchTree( start ){
    return this._searchTree( this.search( start ) );
};

// ============================================================================
var BreadthFirstSearch = function( graph, processFns ){
    var self = this;
    GraphSearch.call( this, graph, processFns );
    return self;
};
BreadthFirstSearch.prototype = new GraphSearch();
BreadthFirstSearch.prototype.constructor = BreadthFirstSearch;

BreadthFirstSearch.prototype._search = function __search( start, search ){
    search = search || {
        discovered : {},
        //parents : {},
        edges : []
    };

    var self = this,
        queue = [];

    function discoverAdjacent( adj, edge ){
        var source = this;
        if( self.processFns.edge ){ self.processFns.edge.call( self, source, edge, search ); }
        if( !search.discovered[ adj.name ] ){
            //console.debug( '\t\t\t', adj.name, 'is undiscovered:', search.discovered[ adj.name ] );
            search.discovered[ adj.name ] = true;
            //search.parents[ adj.name ] = source;
            search.edges.push({ source: source.name, target: adj.name });
            //console.debug( '\t\t\t queuing undiscovered: ', adj );
            queue.push( adj );
        }
    }

    //console.debug( 'BFS starting. start:', start );
    search.discovered[ start.name ] = true;
    queue.push( start );
    while( queue.length ){
        var vertex = queue.shift();
        //console.debug( '\t Queue is shifting. Current:', vertex, 'queue:', queue );
        if( self.processFns.vertexEarly ){ self.processFns.vertexEarly.call( self, vertex, search ); }
        self.graph.eachAdjacent( vertex, discoverAdjacent );
        if( self.processFns.vertexLate ){ self.processFns.vertexLate.call( self, vertex, search ); }
    }
    //console.debug( 'search.edges:', JSON.stringify( search.edges ) );
    return search;
};


// ============================================================================
var DepthFirstSearch = function( graph, processFns ){
    var self = this;
    GraphSearch.call( this, graph, processFns );
    return self;
};
DepthFirstSearch.prototype = new GraphSearch();
DepthFirstSearch.prototype.constructor = DepthFirstSearch;

DepthFirstSearch.prototype._search = function( start, search ){
    //console.debug( 'depthFirstSearch:', start );
    search = search || {
        discovered : {},
        //parents    : {},
        edges      : [],
        entryTimes : {},
        exitTimes  : {}
    };
    var self = this,
        time = 0;

    // discover verts adjacent to the source (this):
    //  processing each edge, saving the edge to the tree, and caching the reverse path with parents
    function discoverAdjacentVertices( adjacent, edge ){
        //console.debug( '\t\t adjacent:', adjacent, 'edge:', edge );
        var sourceVertex = this;
        if( self.processFns.edge ){ self.processFns.edge.call( self, sourceVertex, edge, search ); }
        if( !search.discovered[ adjacent.name ] ){
            //search.parents[ adjacent.name ] = sourceVertex;
            search.edges.push({ source: sourceVertex.name, target: adjacent.name });
            recurse( adjacent );
        }
    }

    // use function stack for DFS stack process verts, times, and discover adjacent verts (recursing into them)
    function recurse( vertex ){
        //console.debug( '\t recursing into: ', vertex );
        search.discovered[ vertex.name ] = true;
        if( self.processFns.vertexEarly ){ self.processFns.vertexEarly.call( self, vertex, search ); }
        search.entryTimes[ vertex.name ] = time++;

        self.graph.eachAdjacent( vertex, discoverAdjacentVertices );

        if( self.processFns.vertexLate ){ self.processFns.vertexLate.call( self, vertex, search ); }
        search.exitTimes[ vertex.name ] = time++;
    }
    // begin recursion with the desired start
    recurse( start );

    return search;
};


// ============================================================================
function Graph( directed, data, options ){
//TODO: move directed to options
    this.directed = directed || false;
    return this.init( options ).read( data );
}
window.Graph = Graph;


Graph.prototype.init = function( options ){
    options = options || {};
    var self = this;

    self.allowReflexiveEdges = options.allowReflexiveEdges || false;

    self.vertices = {};
    self.numEdges = 0;
    return self;
};

Graph.prototype.read = function( data ){
    if( !data ){ return this; }
    var self = this;
    if( data.hasOwnProperty( 'nodes' ) ){ return self.readNodesAndLinks( data ); }
    if( data.hasOwnProperty( 'vertices' ) ){ return self.readVerticesAndEdges( data ); }
    return self;
};

//TODO: the next two could be combined
Graph.prototype.readNodesAndLinks = function( data ){
    if( !( data && data.hasOwnProperty( 'nodes' ) ) ){ return this; }
    //console.debug( 'readNodesAndLinks:', data );
    //console.debug( 'data:\n' + JSON.stringify( data, null, '  ' ) );
    var self = this;
    data.nodes.forEach( function( node ){
        self.createVertex( node.name, node.data );
    });
    //console.debug( JSON.stringify( self.vertices, null, '  ' ) );

    ( data.links || [] ).forEach( function( edge, i ){
        var sourceName = data.nodes[ edge.source ].name,
            targetName = data.nodes[ edge.target ].name;
        self.createEdge( sourceName, targetName, self.directed );
    });
    //self.print();
    //console.debug( JSON.stringify( self.toNodesAndLinks(), null, '  ' ) );
    return self;
};

Graph.prototype.readVerticesAndEdges = function( data ){
    if( !( data && data.hasOwnProperty( 'vertices' ) ) ){ return this; }
    //console.debug( 'readVerticesAndEdges:', data );
    //console.debug( 'data:\n' + JSON.stringify( data, null, '  ' ) );
    var self = this;
    data.vertices.forEach( function( node ){
        self.createVertex( node.name, node.data );
    });
    //console.debug( JSON.stringify( self.vertices, null, '  ' ) );

    ( data.edges || [] ).forEach( function( edge, i ){
        self.createEdge( edge.source, edge.target, self.directed );
    });
    //self.print();
    //console.debug( JSON.stringify( self.toNodesAndLinks(), null, '  ' ) );
    return self;
};

Graph.prototype.createVertex = function( name, data ){
    //console.debug( 'createVertex:', name, data );
    if( this.vertices[ name ] ){ return this.vertices[ name ]; }
    return ( this.vertices[ name ] = new Vertex( name, data ) );
};

Graph.prototype.createEdge = function( sourceName, targetName, directed, data ){
    //note: allows multiple 'equivalent' edges (to/from same source/target)
    //console.debug( 'createEdge:', source, target, directed );
    var isReflexive = sourceName === targetName;
    if( !this.allowReflexiveEdges && isReflexive ){ return null; }

    sourceVertex = this.vertices[ sourceName ];
    targetVertex = this.vertices[ targetName ];
    //note: silently ignores edges from/to unknown vertices
    if( !( sourceVertex && targetVertex ) ){ return null; }

//TODO: prob. move to vertex
    var self = this,
        edge = new Edge( sourceName, targetName, data );
    sourceVertex.edges[ targetName ] = edge;
    sourceVertex.degree += 1;
    self.numEdges += 1;
    
    //TODO:! don't like having duplicate edges for non-directed graphs
    // mirror edges (reversing source and target) in non-directed graphs
    //  but only if not reflexive
    if( !isReflexive && !directed ){
        // flip directed to prevent recursion loop
        self.createEdge( targetName, sourceName, true );
    }

    return edge;
};

Graph.prototype.edges = function( propsOrFn ){
    return Array.prototype.concat.apply( [], this.eachVertex( function( vertex ){
        return vertex.eachEdge( propsOrFn );
    }));
};

Graph.prototype.eachVertex = function( propsOrFn ){
    return iterate( this.vertices, propsOrFn );
};

Graph.prototype.adjacent = function( vertex ){
    var self = this;
    return iterate( vertex.edges, function( edge ){
        return self.vertices[ edge.target ];
    });
};

Graph.prototype.eachAdjacent = function( vertex, fn ){
    var self = this;
    return iterate( vertex.edges, function( edge ){
        var adj = self.vertices[ edge.target ];
        return fn.call( vertex, adj, edge );
    });
};

Graph.prototype.print = function(){
    var self = this;
    console.log( 'Graph has ' + Object.keys( self.vertices ).length + ' vertices' );
    self.eachVertex( function( vertex ){
        console.log( vertex.toString() );
        vertex.eachEdge( function( edge ){
            console.log( '\t ' + edge );
        });
    });
    return self;
};

Graph.prototype.toDOT = function(){
    var self = this,
        strings = [];
    strings.push( 'graph bler {' );
    self.edges( function( edge ){
        strings.push( '\t' + edge.from + ' -- ' + edge.to + ';' );
    });
    strings.push( '}' );
    return strings.join( '\n' );
};

Graph.prototype.toNodesAndLinks = function(){
    var self = this,
        indeces = {};
    return {
        nodes : self.eachVertex( function( vertex, key, i ){
            indeces[ vertex.name ] = i;
            return vertex.toJSON();
        }),
        links : self.edges( function( edge ){
            var json = edge.toJSON();
            json.source = indeces[ edge.source ];
            json.target = indeces[ edge.target ];
            return json;
        })
    };
};

Graph.prototype.toVerticesAndEdges = function(){
    var self = this;
    return {
        vertices : self.eachVertex( function( vertex, key ){
            return vertex.toJSON();
        }),
        edges : self.edges( function( edge ){
            return edge.toJSON();
        })
    };
};

Graph.prototype.breadthFirstSearch = function( start, processFns ){
    return new BreadthFirstSearch( this ).search( start );
};

Graph.prototype.breadthFirstSearchTree = function( start, processFns ){
    return new BreadthFirstSearch( this ).searchTree( start );
};

Graph.prototype.depthFirstSearch = function( start, processFns ){
    return new DepthFirstSearch( this ).search( start );
};

Graph.prototype.depthFirstSearchTree = function( start, processFns ){
    return new DepthFirstSearch( this ).searchTree( start );
};


//Graph.prototype.shortestPath = function( start, end ){
//};
//
//Graph.prototype.articulationVertices = function(){
//};
//
//Graph.prototype.isAcyclic = function(){
//};
//
//Graph.prototype.isBipartite = function(){
//};

Graph.prototype.weakComponents = function(){
//TODO: alternately, instead of returning graph-like objects:
//  - could simply decorate the vertices (vertex.component = componentIndex), or clone the graph and do that
    var self = this,
        searchGraph = this,
        undiscovered,
        components = [];

    function getComponent( undiscoveredVertex ){
//TODO: better interface on dfs (search v. searchTree)
        var search = new DepthFirstSearch( searchGraph )._search( undiscoveredVertex );

        // remove curr discovered from undiscovered
        undiscovered = undiscovered.filter( function( name ){
            return !( name in search.discovered );
        });

        return {
            vertices : Object.keys( search.discovered ).map( function( vertexName ){
                return self.vertices[ vertexName ].toJSON();
            }),
            edges : search.edges.map( function( edge ){
                // restore any reversed edges
                var hasBeenReversed = self.vertices[ edge.target ].edges[ edge.source ] !== undefined;
                if( self.directed && hasBeenReversed ){
                    var swap = edge.source;
                    edge.source = edge.target;
                    edge.target = swap;
                }
                return edge;
            })
        };
    }

    if( self.directed ){
        // if directed - convert to undirected for search
        searchGraph = new Graph( false, self.toNodesAndLinks() );
    }
    undiscovered = Object.keys( searchGraph.vertices );
    //console.debug( '(initial) undiscovered:', undiscovered );
    while( undiscovered.length ){
        var undiscoveredVertex = searchGraph.vertices[ undiscovered.shift() ];
        components.push( getComponent( undiscoveredVertex ) );
        //console.debug( 'undiscovered now:', undiscovered );
    }

    //console.debug( 'components:\n', JSON.stringify( components, null, '  ' ) );
    return components;
};

Graph.prototype.weakComponentGraph = function(){
    //note: although this can often look like the original graph - edges can be lost
    var components = this.weakComponents();
    return new Graph( this.directed, {
        vertices : components.reduce( function( reduction, curr ){
            return reduction.concat( curr.vertices );
        }, [] ),
        edges : components.reduce( function( reduction, curr ){
            return reduction.concat( curr.edges );
        }, [] )
    });
};

Graph.prototype.weakComponentGraphArray = function(){
    //note: although this can often look like the original graph - edges can be lost
    return this.weakComponents().map( function( component ){
        return new Graph( this.directed, component );
    });
};


// ============================================================================



// ============================================================================
function randGraph( directed, numVerts, numEdges ){
    //console.debug( 'randGraph', directed, numVerts, numEdges );
    var data = { nodes : [], links : [] };
    function randRange( range ){
        return Math.floor( Math.random() * range );
    }
    for( var i=0; i<numVerts; i++ ){
        data.nodes.push({ name: i });
    }
    for( i=0; i<numEdges; i++ ){
        data.links.push({
            source : randRange( numVerts ),
            target : randRange( numVerts )
        });
    }
    //console.debug( JSON.stringify( data, null, '  ' ) );
    return new Graph( directed, data );
}


// ============================================================================
    return {
        Vertex : Vertex,
        Edge : Edge,
        BreadthFirstSearch : BreadthFirstSearch,
        DepthFirstSearch : DepthFirstSearch,
        Graph : Graph,
        randGraph : randGraph
    };
});
