// NOTE: use 'sudo npm install .', then 'grunt' to use this file
module.exports = function(grunt) {
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),
        requirejs: {
            compile: {
                options: {
                    baseUrl : "../../../../static/scripts/",
                    paths   : {
                        "plugin": "../../config/plugins/visualizations/charts/static"
                    },
                    shim    : {
                        "libs/underscore": { exports: "_" },
                        "libs/backbone/backbone": { exports: "Backbone" }
                    },
                    name    : "plugin/app",
                    out     : "static/build-app.js",
                }
            }
        }
    });
    grunt.loadNpmTasks('grunt-contrib-requirejs');
    grunt.registerTask( 'default', [ 'requirejs' ]);
};
