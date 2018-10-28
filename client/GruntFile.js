module.exports = function(grunt) {
    var GALAXY_PATHS = {
        dist: "../static/scripts",
        maps: "../static/maps",
        // this symlink allows us to serve uncompressed scripts in DEV_PATH for use with sourcemaps
        srcSymlink: "../static/src"
    };
    var _ = grunt.util._;
    var fmt = _.sprintf;
    var styleDistPath = "../static/style/blue";
    var imagesPath = "../static/images";
    var stylePath = "./galaxy/style/scss";

    grunt.config.set("app", "galaxy");
    grunt.config.set("paths", GALAXY_PATHS);
    /**
     * Grunt task to build static/style resources (css, sprites)
     * @param  {Object} grunt main grunt file
     * @return {Function} callback to build this task
     */
    /* global module */

    // Create sprite images and .less files
    grunt.config("sprite", {
        options: {
            algorithm: "binary-tree"
        },
        "history-buttons": {
            src: fmt("%s/history-buttons/*.png", imagesPath),
            dest: fmt("%s/sprite-history-buttons.png", styleDistPath),
            imgPath: fmt("sprite-history-buttons.png"),
            destCss: fmt("%s/sprite-history-buttons.scss", stylePath)
        },
        "history-states": {
            src: fmt("%s/history-states/*.png", imagesPath),
            dest: fmt("%s/sprite-history-states.png", styleDistPath),
            imgPath: fmt("sprite-history-states.png"),
            destCss: fmt("%s/sprite-history-states.scss", stylePath)
        },
        fugue: {
            src: fmt("%s/fugue/*.png", imagesPath),
            dest: fmt("%s/sprite-fugue.png", styleDistPath),
            imgPath: fmt("sprite-fugue.png"),
            destCss: fmt("%s/sprite-fugue.scss", stylePath)
        }
    });

    grunt.loadNpmTasks("grunt-spritesmith");
    grunt.registerTask("default", ["sprite"]);
};
