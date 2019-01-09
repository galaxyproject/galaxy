var path = require("path");
var fs = require("fs");
var del = require("del");
var _ = require("underscore");

var gulp = require("gulp");
var uglify = require("gulp-uglify");
var babel = require("gulp-babel");

var paths = {
    node_modules: "./node_modules",
    scripts: [
        "galaxy/scripts/**/*.js",
        "!galaxy/scripts/qunit/**/*",
        "!galaxy/scripts/entry/**/*",
        "!galaxy/scripts/libs/**/*"
    ],
    plugin_dirs: ["../config/plugins/**/static/**/*", "!../config/plugins/**/node_modules{,/**}"],
    lib_locs: {
        // This is a stepping stone towards having all this staged
        // automatically.  Eventually, this dictionary and staging step will
        // not be necessary.
        backbone: ["backbone.js", "backbone.js"],
        "bootstrap-tour": ["build/js/bootstrap-tour.js", "bootstrap-tour.js"],
        d3: ["d3.js", "d3.js"],
        "bibtex-parse-js": ["bibtexParse.js", "bibtexParse.js"],
        jquery: ["dist/jquery.js", "jquery/jquery.js"],
        "jquery.complexify": ["jquery.complexify.js", "jquery/jquery.complexify.js"],
        "jquery.cookie": ["jquery.cookie.js", "jquery/jquery.cookie.js"],
        "jquery-migrate": ["dist/jquery-migrate.js", "jquery/jquery.migrate.js"],
        "jquery-mousewheel": ["jquery.mousewheel.js", "jquery/jquery.mousewheel.js"],
        "raven-js": ["dist/raven.js", "raven.js"],
        requirejs: ["require.js", "require.js"],
        underscore: ["underscore.js", "underscore.js"]
    },
    libs: ["galaxy/scripts/libs/**/*.js"]
};

gulp.task("stage-libs", function(callback) {
    _.each(_.keys(paths.lib_locs), function(lib) {
        var p1 = path.resolve(path.join(paths.node_modules, lib, paths.lib_locs[lib][0]));
        var p2 = path.resolve(path.join("galaxy", "scripts", "libs", paths.lib_locs[lib][1]));
        if (fs.existsSync(p1)) {
            del.sync(p2);
            fs.createReadStream(p1).pipe(fs.createWriteStream(p2));
        } else {
            callback(
                p1 +
                    " does not exist, yet it is a required library.  This is an error.  Check that the package in question exists in node_modules."
            );
        }
    });
});

gulp.task("fonts", function() {
    return gulp
        .src(path.resolve(path.join(paths.node_modules, "font-awesome/fonts/**/*")))
        .pipe(gulp.dest("../static/images/fonts"));
});

// TODO: Remove script and lib tasks (for 19.05) once we are sure there are no
// external accessors (via require or explicit inclusion in templates)
gulp.task("scripts", function() {
    return gulp
        .src(paths.scripts)
        .pipe(
            babel({
                plugins: ["transform-es2015-modules-amd"]
            })
        )
        .pipe(uglify())
        .pipe(gulp.dest("../static/scripts/"));
});

gulp.task("libs", function() {
    return gulp
        .src(paths.libs)
        .pipe(uglify())
        .pipe(gulp.dest("../static/scripts/libs/"));
});

gulp.task("plugins", function() {
    return gulp.src(paths.plugin_dirs).pipe(gulp.dest("../static/plugins/"));
});

gulp.task("clean", function() {
    //Wipe out all scripts that aren't handled by webpack
    return del(["../static/scripts/**/*.js", "!../static/scripts/bundled/**.*.js"], { force: true });
});

gulp.task("staging", ["stage-libs", "fonts"]);

gulp.task("default", ["libs", "scripts"]);
