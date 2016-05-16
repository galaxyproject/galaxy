module.exports = function(grunt) {
    "use strict";

    var GALAXY_PATHS = {
            dist        : '../lib/galaxy/web/framework/static/scripts',
            maps        : '../lib/galaxy/web/framework/static/maps',
            // this symlink allows us to serve uncompressed scripts in DEV_PATH for use with sourcemaps
            srcSymlink  : '../lib/galaxy/web/framework/static/src',
        },
        TOOLSHED_PATHS = {
            dist        : '../lib/galaxy/web/framework/static/toolshed/scripts',
            maps        : '../lib/galaxy/web/framework/static/toolshed/maps',
            srcSymlink  : '../lib/galaxy/web/framework/static/toolshed/src',
        };

    grunt.config.set( 'app', 'galaxy' );
    grunt.config.set( 'paths', GALAXY_PATHS );
    if( grunt.option( 'app' ) === 'toolshed' ){
	    grunt.config.set( 'app', grunt.option( 'app' ) );
	    grunt.config.set( 'paths', TOOLSHED_PATHS );
    }

    grunt.loadNpmTasks('grunt-check-modules');
    // see the sub directory grunt-tasks/ for individual task definitions
    grunt.loadTasks( 'grunt-tasks' );
    // note: 'handlebars' *not* 'templates' since handlebars doesn't call uglify
    grunt.registerTask( 'default', [ 'check-modules', 'uglify', 'webpack' ] );
};
