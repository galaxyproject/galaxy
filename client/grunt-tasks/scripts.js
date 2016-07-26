/**
 * Grunt task to compress/bundle static/scripts.
 * @param  {Object} grunt main grunt file
 * @return {Function} callback to build this task
 */
module.exports = function( grunt ){
    "use strict";

    grunt.loadNpmTasks( 'grunt-contrib-watch' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );

    var app = grunt.config.get( 'app' );
    var paths = grunt.config.get( 'paths' );

    // main tasks
    var buildTasks = [ 'uglify' ];
    grunt.registerTask( 'compress', buildTasks );
    grunt.registerTask( 'decompress', function(){
        grunt.log.writeln( "decompressing... (don't forget to call 'grunt' again before committing)" );
        setToBeautify();
        grunt.task.run( buildTasks );
    });

    // -------------------------------------------------------------------------- uglify
    // minification and source maps
    var uglifyTargetFiles = {
        expand : true,
        cwd : paths.srcSymlink,
        src : [
            '**/*.js',
            // ignore webpack apps/bundles, the packed symlink
            '!apps/**/*.js',
            '!bundled/**',
            '!packed/**'
        ],
        dest : paths.dist
    };
    grunt.config( 'uglify', {
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
            }
        },
        target : {
            options : {
                sourceMap : true,
                sourceMapName : function( path ){
                    // rewrite name to have all source maps in 'static/maps'
                    return path.replace( paths.dist, paths.maps ) + '.map';
                }
            },
            files: [ uglifyTargetFiles ],
        }
    });

    // set uglify to make human readable instead, used with the --develop flag and decompress task
    function setToBeautify(){
        grunt.log.writeln( 'using more human readable build settings' );
        // uglify settings used when scripts are decompressed/not-minified
        grunt.config( 'uglify.options', {
            mangle   : false,
            beautify : true,
            compress : {
                drop_debugger : false
            }
        });
    }

    // --develop: allow flag for beautified settings
    if ( grunt.option( 'develop' ) ){
        setToBeautify();
    }

    // -------------------------------------------------------------------------- grunt watch
    grunt.config( 'watch', {
        options : {
            cwd : paths.src,
            spawn : false
        },
        // NOTE: but not in the apps dir (which is only used by webpack)
        compress : {
            files : [ '*.js', '!apps/**' ],
            tasks : [ 'compress' ],
        }
    });

    // ------- build only what was changed
    // cache for a list of files that have changed, to be sent to a debounced change fn
    var changedFiles = [];

    // when files are changed, set the copy src and packScripts target to the filenames of the updated files
    var onChange = grunt.util._.debounce( function() {
        grunt.log.writeln( 'onChange, changedFiles:', changedFiles );
        respecifyTargetSrc( changedFiles );
        changedFiles = [];
    }, 200 );

    /** change the target files for babel and uglify */
    function respecifyTargetSrc( newSrc ) {
        // TODO: make this method generic to any series of tasks (i.e. css watch task)
        uglifyTargetFiles.src = newSrc;
    }

    /** when a change event happens, cache that filepath in changed files and try the debounced change fn */
    grunt.event.on( 'watch', function _addChangedFile( action, filepath, target ){
        // store each filepath in a Files obj, the debounced fn above will use it as an aggregate list for copying
        // we need to take galaxy/scripts out of the filepath or it will be copied to the wrong loc
        filepath = filepath.replace( paths.src + '/', '' );
        grunt.log.writeln( 'on.watch, filepath:', filepath );
        changedFiles.push( filepath );
        onChange();
    });

    // -------------------------------------------------------------------------- --target=<fileA,fileB,...>
    // build only specified files (comma separated)
    // note: these are relative to the paths.src (e.g. galaxy/scripts)
    // example: grunt compress --target=utils/ajax-queue.js,layout/panel.js
    var newTargetSrc = grunt.option( 'target' );
    if( newTargetSrc ){
        newTargetSrc = newTargetSrc.split( ',' );
        grunt.log.writeln( 'only building the following files:', newTargetSrc );
        respecifyTargetSrc( newTargetSrc );
    }
};
