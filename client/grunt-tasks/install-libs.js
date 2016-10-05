/**
 * Grunt task to fetch third-party libraries using bower and copy them to the proper location in client/.
 * @param  {Object} grunt main grunt file
 * @return {Function} callback to build this task
 */
module.exports = function( grunt ){
    "use strict";

    var dev_path = './galaxy/scripts',

        // where to move fetched bower components into the build structure (libName: [ bower-location, libs-location ])
        libraryLocations = {
            'jquery':         [ 'dist/jquery.js', 'jquery/jquery.js' ],
            'jquery-migrate': [ 'jquery-migrate.js', 'jquery/jquery.migrate.js' ],
            'ravenjs':        [ 'dist/raven.js', 'raven.js' ],
            'underscore':     [ 'underscore.js', 'underscore.js' ],
            'backbone':       [ 'backbone.js', 'backbone.js' ],
            'requirejs':      [ 'require.js', 'require.js' ],
            'd3':             [ 'd3.js', 'd3.js' ],
            'bib2json':       [ 'Parser.js', 'bibtex.js' ],

            'farbtastic':     [ 'src/farbtastic.js', 'farbtastic.js' ],
            'jQTouch':        [ 'src/reference/jqtouch.js', 'jquery/jqtouch.js' ],
            'bootstrap-tour': [ 'build/js/bootstrap-tour.js', 'bootstrap-tour.js' ],
            'jquery.complexify':     [ 'jquery.complexify.js', 'jquery.complexify.js' ],

            // these need to be updated and tested
            //'jquery-form': [ 'jquery.form.js', 'jquery/jquery.form.js' ],
            //'jquery-autocomplete': [ 'src/jquery.autocomplete.js', 'jquery/jquery.autocomplete.js' ],
            //'select2': [ 'select2.js', 'jquery/select2.js' ],
            //'jStorage': [ 'jstorage.js', 'jquery/jstorage.js' ],
            //'jquery.cookie': [ '', 'jquery/jquery.cookie.js' ],
            //'dynatree': [ 'dist/jquery.dynatree.js', 'jquery/jquery.dynatree.js' ],
            //'jquery-mousewheel': [ 'jquery.mousewheel.js', 'jquery/jquery.mousewheel.js' ],
            //'jquery.event.drag-drop': [
            //  [ 'event.drag/jquery.event.drag.js', 'jquery/jquery.event.drag.js' ],
            //  [ 'event.drag/jquery.event.drop.js', 'jquery/jquery.event.drop.js' ]
            //],

            // these are complicated by additional css/less
            //'toastr': [ 'toastr.js', 'toastr.js' ],
            //'wymeditor': [ 'dist/wymeditor/jquery.wymeditor.js', 'jquery/jquery.wymeditor.js' ],
            //'jstree': [ 'jstree.js', 'jquery/jstree.js' ],

            // these have been customized by Galaxy
            //'bootstrap': [ 'dist/js/bootstrap.js', 'bootstrap.js' ],
            //'jquery-ui': [
            //  // multiple components now
            //  [ '', 'jquery/jquery-ui.js' ]
            //],

        };

    // call bower to install libraries and other external resources
    grunt.config( 'bower-install-simple', {
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
    });

    /** copy external libraries from bower components to scripts/libs */
    function copyLibs(){
        var lib_path = dev_path + '/libs/';
        for( var libName in libraryLocations ){
            if( libraryLocations.hasOwnProperty( libName ) ){

                var bower_dir = 'bower_components',
                    location = libraryLocations[ libName ],
                    source = [ bower_dir, libName, location[0] ].join( '/' ),
                    destination =  lib_path + location[1];

                grunt.log.writeln( source + ' -> ' + destination );
                grunt.file.copy( source, destination );
            }
        }
    }

    grunt.loadNpmTasks( 'grunt-bower-install-simple' );

    grunt.registerTask( 'copy-libs', 'copy external libraries to src', copyLibs );
    grunt.registerTask( 'install-libs', 'fetch external libraries and copy to src',
                      [ 'bower-install-simple:prod', 'copy-libs' ] );
};
