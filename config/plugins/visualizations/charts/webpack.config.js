var path = require( 'path' );
var root = path.join( __dirname, 'static/repository' );
var grunt = require( 'grunt' );
var registry_json = grunt.file.readJSON( root + '/registry.json' );

// helper to visit registry values
var visit = function( callback ) {
    for ( var lib in registry_json ) {
        var plugins = registry_json[ lib ];
        for ( var i in plugins ) {
            var plugin = plugins[ i ];
            callback( lib, plugin );
        }
    }
};

// identify entries from registry
var entry = { registry : root + '/build/registry.tmp.js' };
visit( function( lib, plugin ) {
    if ( !grunt.file.exists( root + '/build/' + lib + '_' + plugin + '.js' ) ) {
        entry[ lib + '_' + plugin ] = root + '/visualizations/' + lib + '/' + plugin + '/wrapper.js';
        grunt.log.writeln( 'Adding ' + lib + '_' + plugin + '.' );
    }
});

// build registry file
var registry = 'define( [], function() { return {';
visit( function( lib, plugin ) {
    registry += lib + '_' + plugin + ':' + 'require( "visualizations/' + lib + '/' + plugin + '/config" ), ';
});
registry = registry.substr( 0, registry.length - 1 ) + '} } );';
grunt.file.write( root + '/build/registry.tmp.js', registry );
grunt.log.writeln( 'Writing Registry.' );

// configure webpack
module.exports = {
    devtool : 'source-map',
    entry   : entry,
    output  : {
        path            : root + '/build',
        filename        : '[name].js',
        libraryTarget   : 'amd'
    },
    resolve : {
        root : root
    }
};
