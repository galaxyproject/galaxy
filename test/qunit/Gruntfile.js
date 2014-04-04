module.exports = function(grunt) {
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
 
    qunit: {
      all: ['tests/**/*.html'],
      options: {
      }
    },

  });

  grunt.loadNpmTasks('grunt-contrib-qunit');
  // register one or more task lists (you should ALWAYS have a "default" task list)
  grunt.registerTask('default', ['qunit']);
};

