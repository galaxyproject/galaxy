module.exports = function( grunt ){
    "use strict";

    var DIST_PATH = '../static/scripts',
        MAPS_PATH = '../static/maps',
        // this symlink allows us to serve uncompressed scripts in DEV_PATH for use with sourcemaps
        SRC_SYMLINK = '../static/src';

    // compress javascript
    grunt.config( 'uglify', {
        target : {
            files: [{
                expand : true,
                cwd : SRC_SYMLINK,
                src : '**/*.js',
                dest : DIST_PATH
            }],
            options : {
                sourceMap : true,
                sourceMapName : function( path ){
                    // rewrite name to have all source maps in 'static/maps'
                    return path.replace( DIST_PATH, MAPS_PATH ) + '.map';
                }
            }
        },
        options : {
            mangle : {
                screw_ie8 : true
            },
            compress : {
                // high compression options
                screw_ie8 : true,
                sequences: true,
                dead_code : true,
                drop_debugger : true,
                comparisons : true,
                conditionals : true,
                evaluate : true,
                booleans : true,
                loops : true,
                unused : true,
                hoist_funs : true,
                if_return : true,
                join_vars : true,
                cascade : true,
                // drop_console : true
            }
        }
    });

    // use 'grunt watch' (from a new tab in your terminal) to have grunt re-copy changed files automatically
    grunt.config( 'watch', {
        watch: {
            // watch for changes in the src dir
            files: [ SRC_SYMLINK + '/**' ],
            tasks: [ 'uglify' ],
            // tasks: [ 'copy', 'pack' ],
            options: {
                spawn: false
            }
        },
    });

    // -------------------------------------------------------------------------- decompress for easier debugging
    grunt.registerTask( 'decompress', function(){
        grunt.log.writeln( "decompressing... (don't forget to call 'grunt' again before committing)" );
        grunt.config( 'uglify.options', { beautify: true });
        grunt.config( 'uglify.target.options', {});
        grunt.task.run( 'uglify' );
    });
    // alias for symmetry
    grunt.registerTask( 'compress', [ 'uglify' ] );

    // -------------------------------------------------------------------------- copy,pack only those changed
    // adapted from grunt-contrib-watch jslint example
    //TODO: a bit hacky and there's prob. a better way
    //NOTE: copy will fail silently if a file isn't found

    // outer scope variable for the event handler and onChange fn - begin with empty hash
    var changedFiles = Object.create(null);

    // when files are changed, set the copy src and packScripts target to the filenames of the updated files
    var onChange = grunt.util._.debounce(function() {
        grunt.log.writeln( 'onChange, changedFiles:', Object.keys( changedFiles ) );
        grunt.config( 'uglify.target.files', [{
            expand : true,
            cwd : SRC_SYMLINK,
            src : Object.keys( changedFiles ),
            dest : DIST_PATH
        }]);
        changedFiles = Object.create(null);
    }, 200);

    grunt.event.on( 'watch', function( action, filepath ) {
        // store each filepath in a Files obj, the debounced fn above will use it as an aggregate list for copying
        // we need to take galaxy/scripts out of the filepath or it will be copied to the wrong loc
        filepath = filepath.replace( SRC_SYMLINK + '/', '' );
        grunt.log.writeln( 'on.watch, filepath:', filepath );
        changedFiles[filepath] = action;
        onChange();
    });


    grunt.loadNpmTasks( 'grunt-contrib-watch' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );
};