module.exports = function( grunt ){
    grunt.initConfig({
        pkg: grunt.file.readJSON( 'package.json' ),

        qunit: {
            all: [ 'tests/**/*.html' ],
            options: {
            }
        },

        watch: {
            // watch for changes in the src dir
            files: [ 'tests/**.js', '../../static/scripts/**/**.js' ],
            tasks: [ 'default' ]
        }
    });

    // use 'grunt --test=my-tests.html' or 'grunt watch --test=my-tests.html'
    //  to only run the tests in tests/my-tests.html
    if( grunt.option( 'test' ) ){
        grunt.config.set( 'qunit.all', 'tests/' + grunt.option( 'test' ) );
        grunt.log.writeln( '(only testing ' + grunt.config.get( 'qunit.all' ) + ')' );
    }

    grunt.loadNpmTasks( 'grunt-contrib-qunit' );

    // use 'grunt watch' to have the qunit tests run when scripts or tests are changed
    grunt.loadNpmTasks( 'grunt-contrib-watch' );

    // register one or more task lists (you should ALWAYS have a "default" task list)
    grunt.registerTask( 'default', [ 'qunit' ] );
};

