/**
 * Grunt task to compile templates.
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
                dest : paths.srcSymlink + '/templates/compiled',
                ext : '.js'
            }],
            options : {
                namespace : 'Handlebars.templates',
                // generates the key under the namespace above where the template fns are accessed
                processName : function( filepath ){
                    filepath = filepath.match( /.*\/(\w+)\.handlebars/ ).pop();
                    return filepath;
                },
                wrapped : true
            }
        }
    });

    grunt.registerTask( 'templates', function(){
        // compile then compress
        grunt.task.run( 'handlebars' );
        grunt.config( 'uglify.target.files', [{
            expand : true,
            cwd : paths.srcSymlink + '/templates/compiled',
            src : '**/*.js',
            dest : paths.dist + '/templates/compiled'
        }]);
        grunt.task.run( 'uglify' );
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