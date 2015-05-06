module.exports = function(grunt) {
    var DEV_PATH = './galaxy/scripts',
        DIST_PATH = '../static/scripts',
        MAPS_PATH = '../static/maps',
        // this symlink allows us to serve uncompressed scripts in DEV_PATH for use with sourcemaps
        SRC_SYMLINK = '../static/src';

    // Project configuration.
    grunt.initConfig({
        pkg: grunt.file.readJSON( 'package.json' ),

        uglify: {
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
        },

        // use 'grunt watch' (from a new tab in your terminal) to have grunt re-copy changed files automatically
        watch: {
            // watch for changes in the src dir
            files: [ SRC_SYMLINK + '/**' ],
            tasks: [ 'uglify' ],
            // tasks: [ 'copy', 'pack' ],
            options: {
                spawn: false
            }
        },

        // call bower to install libraries and other external resources
        "bower-install-simple" : {
            options: {
                color: true
            },
            "prod": {
                options: {
                    production: true
                }
            },
            "dev": {
                options: {
                    production: false
                }
            }
        },
        // where to move fetched bower components into the build structure (libName: [ bower-location, libs-location ])
        libraryLocations : {
            "jquery":         [ "dist/jquery.js", "jquery/jquery.js" ],
            "jquery-migrate": [ "jquery-migrate.js", "jquery/jquery.migrate.js" ],
            "traceKit":       [ "tracekit.js", "tracekit.js" ],
            "ravenjs":        [ "dist/raven.js", "raven.js" ],
            "underscore":     [ "underscore.js", "underscore.js" ],
            "handlebars":     [ "handlebars.runtime.js", "handlebars.runtime.js" ],
            "backbone":       [ "backbone.js", "backbone/backbone.js" ],

            // these need to be updated and tested
            //"require": [ "build/require.js", "require.js" ],
            //"d3": [ "d3.js", "d3.js" ],
            //"farbtastic": [ "src/farbtastic.js", "farbtastic.js" ],
            //"jQTouch": [ "src/reference/jqtouch.js", "jquery/jqtouch.js" ],
            //"bib2json": [ "Parser.js", "bibtex.js" ],
            //"jquery-form": [ "jquery.form.js", "jquery/jquery.form.js" ],
            //"jquery-autocomplete": [ "src/jquery.autocomplete.js", "jquery/jquery.autocomplete.js" ],
            //"select2": [ "select2.js", "jquery/select2.js" ],
            //"jStorage": [ "jstorage.js", "jquery/jstorage.js" ],
            //"jquery.cookie": [ "", "jquery/jquery.cookie.js" ],
            //"dynatree": [ "dist/jquery.dynatree.js", "jquery/jquery.dynatree.js" ],
            //"jquery-mousewheel": [ "jquery.mousewheel.js", "jquery/jquery.mousewheel.js" ],
            //"jquery.event.drag-drop": [
            //  [ "event.drag/jquery.event.drag.js", "jquery/jquery.event.drag.js" ],
            //  [ "event.drag/jquery.event.drop.js", "jquery/jquery.event.drop.js" ]
            //],

            // these are complicated by additional css/less
            //"toastr": [ "toastr.js", "toastr.js" ],
            //"wymeditor": [ "dist/wymeditor/jquery.wymeditor.js", "jquery/jquery.wymeditor.js" ],
            //"jstree": [ "jstree.js", "jquery/jstree.js" ],

            // these have been customized by Galaxy
            //"bootstrap": [ "dist/js/bootstrap.js", "bootstrap.js" ],
            //"jquery-ui": [
            //  // multiple components now
            //  [ "", "jquery/jquery-ui.js" ]
            //],

        }

    });

    grunt.loadNpmTasks( 'grunt-contrib-watch' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );
    grunt.loadNpmTasks( 'grunt-bower-install-simple');

    grunt.registerTask( 'default', [ 'uglify' ] );

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

    // -------------------------------------------------------------------------- fetch/update external libraries
    /** copy external libraries from bower components to scripts/libs */
    function copyLibs(){
        var LIB_PATH = DEV_PATH + '/libs/',
            libraryLocations = grunt.config( 'libraryLocations' );
        for( var libName in libraryLocations ){
            if( libraryLocations.hasOwnProperty( libName ) ){
                var BOWER_DIR = 'bower_components',
                    location = libraryLocations[ libName ],
                    source = [ BOWER_DIR, libName, location[0] ].join( '/' ),
                    destination =  LIB_PATH + location[1];
                grunt.log.writeln( source + ' -> ' + destination );
                grunt.file.copy( source, destination );
            }
        }
    }

    grunt.registerTask( 'copy-libs', 'copy external libraries to src', copyLibs );
    grunt.registerTask( 'install-libs', 'fetch external libraries and copy to src',
                      [ 'bower-install-simple:prod', 'copy-libs' ] );

};
