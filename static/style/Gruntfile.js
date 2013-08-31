/* jshint node: true */

module.exports = function(grunt) {
  "use strict";
  
  var lessFiles = [ 'base', 'autocomplete_tagging', 'embed_item', 'iphone', 'masthead', 'library', 'trackster' ];

  var _ = grunt.util._; 
  var fmt = _.sprintf; 

  // Project configuration.
  grunt.initConfig({

    // Metadata.
    pkg: grunt.file.readJSON('package.json'),

    recess: {
      options: {
        compile: true,
        compress: true,
        includePath: 'blue'
      },
      dist: {
        files: _.reduce( lessFiles, function( d, s ) { 
          d[ fmt( 'blue/%s.css', s ) ] = [ fmt( 'src/less/%s.less', s ) ]; return d 
        }, {} )
      }
    },
  });

  // These plugins provide necessary tasks.
  grunt.loadNpmTasks('grunt-recess');

  // Default task.
  grunt.registerTask('default', ['recess']);

};
