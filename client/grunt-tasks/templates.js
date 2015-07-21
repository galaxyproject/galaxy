/**
 * Grunt task to compile handlebars templates.
 * @param  {Object} grunt main grunt file
 * @return {Function} callback to build this task
 */
module.exports = function( grunt ){
    "use strict";

    var app = grunt.config.get( 'app' ),
        paths = grunt.config.get( 'paths' );

    grunt.config( 'handlebars', {
        'default' : {
            files: [{
                expand : true,
                cwd : paths.srcSymlink + '/templates',
                src : '**/*.handlebars',
                dest : paths.dist + '/templates'
            }],
            options : {
            }
        }
    });

    // -------------------------------------------------------------------------- watch & compile
    // grunt.config( 'watch', {
    //     watch: {
    //         // watch for changes in the src dir
    //         files: [ paths.srcSymlink + '/**' ],
    //         tasks: [ 'uglify' ],
    //         options: {
    //             spawn: false
    //         }
    //     }
    // });

    // --------------------------------------------------------------------------
    grunt.loadNpmTasks( 'grunt-contrib-handlebars' );
};