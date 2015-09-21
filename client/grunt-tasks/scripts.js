/**
 * Grunt task to compress/bundle static/scripts.
 * @param  {Object} grunt main grunt file
 * @return {Function} callback to build this task
 */
module.exports = function( grunt ){
    "use strict";

    var app = grunt.config.get( 'app' ),
        paths = grunt.config.get( 'paths' );

    grunt.config( 'uglify', {
        target : {
            files: [{
                expand : true,
                cwd : paths.srcSymlink,
                src : '**/*.js',
                dest : paths.dist
            }],
        }
    });

    if (grunt.option('develop')){
        grunt.config( 'uglify.options', {
            beautify : true,
            compress : {
                drop_debugger : false
            }
        });
    } else {
        grunt.config( 'uglify.target.options', {
            sourceMap : true,
            sourceMapName : function( path ){
                // rewrite name to have all source maps in 'static/maps'
                return path.replace( paths.dist, paths.maps ) + '.map';
            }
        });
        grunt.config( 'uglify.options', {
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
                drop_console : true
            }
        });
    }


    // -------------------------------------------------------------------------- decompress for easier debugging
    grunt.registerTask( 'decompress', function(){
        grunt.log.writeln( "decompressing... (don't forget to call 'grunt' again before committing)" );
        grunt.config( 'uglify.options', { beautify: true });
        grunt.config( 'uglify.target.options', {});
        grunt.task.run( 'uglify' );
    });
    // alias for symmetry
    grunt.registerTask( 'compress', [ 'uglify' ] );

    // -------------------------------------------------------------------------- watch & copy,pack only those changed
    // use 'grunt watch' (from a new tab in your terminal) to have grunt re-copy changed files automatically
    grunt.config( 'watch', {
        watch: {
            // watch for changes in the src dir
            files: [ paths.srcSymlink + '/**' ],
            tasks: [ 'uglify' ],
            options: {
                spawn: false
            }
        }
    });


    // outer scope variable for the event handler and onChange fn - begin with empty hash
    var changedFiles = Object.create(null);

    // when files are changed, set the copy src and packScripts target to the filenames of the updated files
    var onChange = grunt.util._.debounce(function() {
        grunt.log.writeln( 'onChange, changedFiles:', Object.keys( changedFiles ) );
        grunt.config( 'uglify.target.files', [{
            expand : true,
            cwd : paths.srcSymlink,
            src : Object.keys( changedFiles ),
            dest : paths.dist
        }]);
        changedFiles = Object.create(null);
    }, 200);

    var addChangedFile = function( action, filepath ) {
        // store each filepath in a Files obj, the debounced fn above will use it as an aggregate list for copying
        // we need to take galaxy/scripts out of the filepath or it will be copied to the wrong loc
        filepath = filepath.replace( paths.srcSymlink + '/', '' );
        // grunt.log.writeln( 'on.watch, filepath:', filepath );
        changedFiles[ filepath ] = action;
        onChange();
    };
    grunt.event.on( 'watch', addChangedFile );

    // --------------------------------------------------------------------------
    grunt.loadNpmTasks( 'grunt-contrib-watch' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );
};
