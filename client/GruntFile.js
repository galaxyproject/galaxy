module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON( 'package.json' ),

    // default task
    // use 'grunt copy' to copy the entire <galaxy>/client/galaxy/scripts dir into <galaxy>/static/scripts
    copy: {
      main: {
        files: [
          {
            expand : true,
            cwd : 'galaxy/scripts/',
            src : '**',
            dest : '../static/scripts'
          }
        ]
      }
    },

    // use 'grunt watch' (from a new tab in your terminal) to have grunt re-copy changed files automatically
    watch: {
        // watch for changes in the src dir
        files: [ 'galaxy/scripts/**' ],
        tasks: [ 'copy' ],
        options: {
          spawn: false
        }
    }
  });

  grunt.loadNpmTasks( 'grunt-contrib-watch' );
  grunt.loadNpmTasks( 'grunt-contrib-copy');

  // adapted from grunt-contrib-watch jslint example
  //TODO: a bit hacky and there's prob. a better way
  //NOTE: copy will fail silently if a file isn't found
  var changedFiles = Object.create(null);
  var onChange = grunt.util._.debounce(function() {
    grunt.config( 'copy.main.files', [{
      expand: true,
      cwd: 'galaxy/scripts',
      src: Object.keys( changedFiles ),
      dest: '../static/scripts/'
    }]);
    changedFiles = Object.create(null);
  }, 200);
  grunt.event.on('watch', function(action, filepath) {
    // store each filepath in a Files obj, the debounced fn above will use it as an aggregate list for copying
    // we need to take galaxy/scripts out of the filepath or it will be copied to the wrong loc
    filepath = filepath.replace( /galaxy\/scripts\//, '' );
    changedFiles[filepath] = action;
    onChange();
  });

  grunt.registerTask( 'default', [ 'copy' ] );
};
