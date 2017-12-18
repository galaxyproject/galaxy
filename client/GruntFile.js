module.exports = function(grunt) {
    var GALAXY_PATHS = {
        dist: "../static/scripts",
        maps: "../static/maps",
        // this symlink allows us to serve uncompressed scripts in DEV_PATH for use with sourcemaps
        srcSymlink: "../static/src"
    };
    grunt.config.set("app", "galaxy");
    grunt.config.set("paths", GALAXY_PATHS);
    // see the sub directory grunt-tasks/ for individual task definitions
    grunt.loadTasks("grunt-tasks");
    grunt.registerTask("default", ["style"]);
};
