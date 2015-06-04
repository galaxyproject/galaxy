module.exports = function(grunt) {
    "use strict";

    // see the sub directory grunt-tasks/ for individual task definitions
    grunt.loadTasks( 'grunt-tasks' );
    grunt.registerTask( 'default', [ 'uglify' ] );
};
