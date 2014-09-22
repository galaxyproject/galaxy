/* jshint node: true */

module.exports = function(grunt) {
  "use strict";
  
  var theme = grunt.option( 'theme', 'blue' );

  var out = 'blue';
  var lessFiles = [
    'base',
    'autocomplete_tagging',
    'embed_item',
    'iphone',
    'masthead',
    'library',
    'trackster',
    'circster',
    'jstree'
  ];

  var _ = grunt.util._;
  var fmt = _.sprintf;

  // Project configuration.
  grunt.initConfig({

    // Metadata.
    pkg: grunt.file.readJSON('package.json'),

    // Create sprite images and .less files
    sprite : {
      options: {
        algorithm: 'binary-tree'
      },
      'history-buttons': {
        src: '../images/history-buttons/*.png',
        destImg: fmt( '%s/sprite-history-buttons.png', out ),
        destCSS: fmt( '%s/sprite-history-buttons.less', out )
      },
      'history-states': {
        src: '../images/history-states/*.png',
        destImg: fmt( '%s/sprite-history-states.png', out ),
        destCSS: fmt( '%s/sprite-history-states.less', out )
      },
      'fugue': {
        src: '../images/fugue/*.png',
        destImg: fmt( '%s/sprite-fugue.png', out ),
        destCSS: fmt( '%s/sprite-fugue.less', out )
      }
    },

    // Compile less files
    less: {
      options: {
        compress: true,
        paths: [ out ]
      },
      dist: {
        files: _.reduce( lessFiles, function( d, s ) {
          d[ fmt( '%s/%s.css', out, s ) ] = [ fmt( 'src/less/%s.less', s ) ]; return d;
        }, {} )
      }
    },

    // remove tmp files
    clean: {
      clean : [ fmt('%s/tmp-site-config.less', out) ]
    }
  });

  // Write theme variable for less
  grunt.registerTask('less-site-config', 'Write site configuration for less', function() {
    grunt.file.write( fmt('%s/tmp-site-config.less', out), fmt( "@theme-name: %s;", theme ) );
  });

  // These plugins provide necessary tasks.
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-spritesmith');
  grunt.loadNpmTasks('grunt-contrib-clean');

  // Default task.
  grunt.registerTask('default', ['sprite', 'less-site-config', 'less', 'clean']);

};
