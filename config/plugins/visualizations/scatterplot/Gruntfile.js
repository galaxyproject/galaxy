// NOTE: use 'sudo npm install .', then 'grunt' to use this file

module.exports = function(grunt) {

    grunt.initConfig({
        pkg: grunt.file.readJSON( 'package.json' ),

        handlebars: {
            // compile all hb templates into a single file in the build dir
            compile: {
                options: {
                    namespace: 'scatterplot',
                    processName : function( filepath ){
                        return filepath.match( /\w*\.handlebars/ )[0].replace( '.handlebars', '' );
                    }
                },
                files: {
                    "build/compiled-templates.js" : "src/handlebars/*.handlebars"
                }
            }
        },

        concat: {
            // concat the template file and any js files in the src dir into a single file in the build dir
            options: {
                separator: ';\n'
            },
            dist: {
                //NOTE: mvc references templates - templates must be cat'd first
                src : [ 'build/compiled-templates.js', 'src/**/*.js' ],
                dest: 'build/scatterplot-concat.js'
            }
        },

        uglify: {
            // uglify the concat single file directly into the static dir
            options: {
                // uncomment these to allow better source mapping during development
                //mangle      : false,
                //beautify    : true
            },
            dist: {
                src : 'build/scatterplot-concat.js',
                dest: 'static/scatterplot-edit.js'
            }
        },

        watch: {
            // watch for changes in the src dir
            files: [ 'src/**.js', 'src/handlebars/*.handlebars' ],
            tasks: [ 'default' ]
        }
    });

    grunt.loadNpmTasks( 'grunt-contrib-handlebars' );
    grunt.loadNpmTasks( 'grunt-contrib-concat' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );
    grunt.loadNpmTasks( 'grunt-contrib-watch' );

    grunt.registerTask( 'default', [ 'handlebars', 'concat', 'uglify' ]);
    // you can run grunt watch directly:
    //  grunt watch
};
