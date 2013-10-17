// NOTE: use 'sudo npm install .', then 'grunt' to use this file

module.exports = function(grunt) {

    grunt.initConfig({
        pkg: grunt.file.readJSON( 'package.json' ),

        handlebars: {
            compile: {
                options: {
                    namespace: 'Templates',
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
            options: {
            },
            dist: {
                src : 'build/scatterplot-concat.js',
                // uglify directly into static dir
                dest: 'static/scatterplot.js'
            }
        },

        watch: {
            files: [ 'src/**.js', 'src/handlebars/*.handlebars' ],
            tasks: [ 'default' ]
        }
    });

    grunt.loadNpmTasks( 'grunt-contrib-handlebars' );
    grunt.loadNpmTasks( 'grunt-contrib-concat' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );
    grunt.loadNpmTasks( 'grunt-contrib-watch' );

    grunt.registerTask( 'default', [ 'handlebars', 'concat', 'uglify' ]);
    grunt.registerTask( 'watch',   [ 'handlebars', 'concat', 'uglify', 'watch' ]);
};
