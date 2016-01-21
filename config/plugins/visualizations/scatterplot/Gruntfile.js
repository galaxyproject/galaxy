// NOTE: use 'sudo npm install .', then 'grunt' to use this file

module.exports = function(grunt) {

    grunt.initConfig({
        pkg: grunt.file.readJSON( 'package.json' ),

        concat: {
            // concat any js files in the src dir into a single file in the build dir
            options: {
                separator: ';\n'
            },
            dist: {
                src : [ 'src/**/*.js' ],
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
            files: [ 'src/**.js' ],
            tasks: [ 'default' ]
        }
    });

    grunt.loadNpmTasks( 'grunt-contrib-concat' );
    grunt.loadNpmTasks( 'grunt-contrib-uglify' );
    grunt.loadNpmTasks( 'grunt-contrib-watch' );

    grunt.registerTask( 'default', [ 'concat', 'uglify' ]);
    // you can run grunt watch directly:
    //  grunt watch
};
