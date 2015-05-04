module.exports = function(grunt) {
    "use strict";

    grunt.loadTasks( 'grunt-tasks' );
    grunt.registerTask( 'default', [ 'uglify' ] );
};
