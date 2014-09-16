module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON( 'package.json' ),

    // default task
    // use 'grunt copy' to copy the entire <galaxy>/client/galaxy/scripts dir into <galaxy>/static/scripts
    copy: {
      main: {
        expand: true,
        cwd: 'galaxy/scripts/',
        src: '**',
        dest: '../static/scripts/'
      }
    },

    // use 'grunt watch' (from a new tab in your terminal) to have grunt re-copy changed files automatically
    watch: {
        // watch for changes in the src dir
        files: [ 'galaxy/scripts/**' ],
        tasks: [ 'default' ]
    }
  });

  grunt.loadNpmTasks( 'grunt-contrib-watch' );
  grunt.loadNpmTasks( 'grunt-contrib-copy');

  grunt.registerTask( 'default', [ 'copy' ] );
};
