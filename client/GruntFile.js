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

    // use 'grunt pack' to call pack_scripts.py to pack all or selected files in static/scripts
    exec: {
      packScripts: {
        cwd: '../static/scripts',
        target: [],
        cmd: function(){
          var targets = grunt.config( 'exec.packScripts.target' );
          // if nothing was passed in pack all scripts
          if( !targets.length ){
            return './pack_scripts.py';
          }

          grunt.log.write( 'packing: ' + targets + '\n' );
          return targets.map( function( target ){
            return './pack_scripts.py ' + target;
          }).join( '; ' );
        }
      }
    },

    // use 'grunt watch' (from a new tab in your terminal) to have grunt re-copy changed files automatically
    watch: {
        // watch for changes in the src dir
        files: [ 'galaxy/scripts/**' ],
        tasks: [ 'copy', 'pack' ],
        options: {
          spawn: false
        }
    }
  });

  grunt.loadNpmTasks( 'grunt-contrib-watch' );
  grunt.loadNpmTasks( 'grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-exec');

  grunt.registerTask( 'pack', [ 'exec' ] );
  grunt.registerTask( 'default', [ 'copy', 'pack' ] );

  // -------------------------------------------------------------------------- copy,pack only those changed
  // adapted from grunt-contrib-watch jslint example
  //TODO: a bit hacky and there's prob. a better way
  //NOTE: copy will fail silently if a file isn't found

  // outer scope variable for the event handler and onChange fn - begin with empty hash
  var changedFiles = Object.create(null);

  // when files are changed, set the copy src and packScripts target to the filenames of the updated files
  var onChange = grunt.util._.debounce(function() {
    grunt.config( 'copy.main.files', [{
      expand: true,
      cwd: 'galaxy/scripts',
      src: Object.keys( changedFiles ),
      dest: '../static/scripts/'
    }]);
    grunt.config( 'exec.packScripts.target', Object.keys( changedFiles ) );
    changedFiles = Object.create(null);
  }, 200);

  grunt.event.on('watch', function(action, filepath) {
    // store each filepath in a Files obj, the debounced fn above will use it as an aggregate list for copying
    // we need to take galaxy/scripts out of the filepath or it will be copied to the wrong loc
    filepath = filepath.replace( /galaxy\/scripts\//, '' );
    changedFiles[filepath] = action;
    onChange();
  });

};
