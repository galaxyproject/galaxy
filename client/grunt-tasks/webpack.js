/**
 * Grunt task to bundle apps using webpack (see also ../webpack.config.js).
 */
module.exports = function( grunt ){
    "use strict";

    var path = require( 'path' );

    // there is a taskrunner specifically for this - but it's not straightforward
    // and duplicates some of the config/code in webpack.config,
    // https://github.com/webpack/grunt-webpack
    // http://webpack.github.io/docs/usage-with-grunt.html

    // so we'll use grunt-exec and call the webpack cli instead (until CLI and runner are unified a bit more?)

    grunt.loadNpmTasks( 'grunt-exec' );

    function webpackCLI(){
        var args = Array.prototype.slice.call( arguments );
        args.unshift( path.join( __dirname, '../node_modules/webpack/bin/webpack.js' ) );
        return args.join( ' ' );
    }
    grunt.registerTask( 'webpack', function(){
        grunt.log.writeln( 'bundling webpack apps for production...' );
        grunt.config( 'exec.webpack-production.command', webpackCLI( '-p' ) );
        grunt.task.run( 'exec:webpack-production' );
    });
    grunt.registerTask( 'webpack-dev', function(){
        grunt.log.writeln( 'bundling webpack apps for development...' );
        grunt.config( 'exec.webpack-dev.command', webpackCLI( '-d' ) );
        grunt.task.run( 'exec:webpack-dev' );
    });
    grunt.registerTask( 'webpack-watch', function(){
        grunt.log.writeln( 'bundling webpack apps for development and watching for changes...' );
        grunt.config( 'exec.webpack-watch.command', webpackCLI( '-d', '--watch' ) );
        grunt.task.run( 'exec:webpack-watch' );
    });
};
