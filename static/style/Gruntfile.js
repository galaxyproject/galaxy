/* jshint node: true */

module.exports = function(grunt) {
  "use strict";

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
      bootstrap: {
        src: ['base.less'],
        dest: 'blue/base.css',
      }
    },
  });

  // These plugins provide necessary tasks.
  grunt.loadNpmTasks('grunt-recess');

  // Default task.
  grunt.registerTask('default', ['recess']);

};
