const path = require("path");
const fs = require("fs");
const del = require("del");
const { src, dest, series, parallel } = require("gulp");
const child_process = require("child_process");
const glob = require("glob");

const paths = {
    node_modules: "./node_modules",
    plugin_dirs: [
        "../config/plugins/{visualizations,interactive_environments}/*/static/**/*",
        "../config/plugins/{visualizations,interactive_environments}/*/*/static/**/*",
    ],
    /*
     * We'll want a flexible glob down the road, but for now there are no
     * un-built visualizations in the repository; for performance and
     * simplicity just add them one at a time until we upgrade older viz's.
     */
    //plugin_build_dirs: [
    //    "../config/plugins/{visualizations,interactive_environments}/*/package.json",
    //    "../config/plugins/{visualizations,interactive_environments}/*/*/package.json"
    //],
    plugin_build_dirs: ["../config/plugins/visualizations/{annotate_image,hyphyvision,openlayers,chiraviz,editor}/package.json"],
    lib_locs: {
        // This is a stepping stone towards having all this staged
        // automatically.  Eventually, this dictionary and staging step will
        // not be necessary.
        backbone: ["backbone.js", "backbone.js"],
        "bootstrap-tour": ["build/js/bootstrap-tour.js", "bootstrap-tour.js"],
        jquery: ["dist/jquery.js", "jquery/jquery.js"],
        "jquery.complexify": ["jquery.complexify.js", "jquery/jquery.complexify.js"],
        "jquery.cookie": ["jquery.cookie.js", "jquery/jquery.cookie.js"],
        "jquery-migrate": ["dist/jquery-migrate.js", "jquery/jquery.migrate.js"],
        "jquery-mousewheel": ["jquery.mousewheel.js", "jquery/jquery.mousewheel.js"],
        "raven-js": ["dist/raven.js", "raven.js"],
        requirejs: ["require.js", "require.js"],
        underscore: ["underscore.js", "underscore.js"],
    },
    libs: ["galaxy/scripts/libs/**/*.js"],
};

function stageLibs(callback) {
    Object.keys(paths.lib_locs).forEach((lib) => {
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
    return callback();
}

function fonts() {
    return src(path.resolve(path.join(paths.node_modules, "font-awesome/fonts/**/*"))).pipe(
        dest("../static/images/fonts")
    );
}

function stagePlugins() {
    return src(paths.plugin_dirs).pipe(dest("../static/plugins/"));
}

function buildPlugins(callback) {
    /*
     * Walk plugin_build_dirs glob and attempt to build modules.
     * */
    paths.plugin_build_dirs.map((build_dir) => {
        glob(build_dir, {}, (er, files) => {
            files.map((file) => {
                let skip_build = false;
                const f = path.join(process.cwd(), file).slice(0, -12);
                const plugin_name = path.dirname(file).split(path.sep).pop();
                const hash_file_path = path.join(f, "static", "plugin_build_hash.txt");

                if (fs.existsSync(hash_file_path)) {
                    skip_build =
                        child_process.spawnSync("git", ["diff", "--quiet", `$(cat ${hash_file_path})`, "--", f], {
                            stdio: "inherit",
                            shell: true,
                        }).status === 0;
                } else {
                    console.log(`No build hashfile detected for ${plugin_name}, generating now.`);
                }

                if (skip_build) {
                    console.log(`No changes detected for ${plugin_name}`);
                } else {
                    console.log(`Installing Dependencies for ${plugin_name}`);
                    child_process.spawnSync(
                        "yarn",
                        ["install", "--production=false", "--network-timeout=300000", "--check-files"],
                        {
                            cwd: f,
                            stdio: "inherit",
                            shell: true,
                        }
                    );
                    console.log(`Building ${plugin_name}`);
                    child_process.spawnSync("yarn", ["build"], { cwd: f, stdio: "inherit", shell: true });
                    child_process.exec(`(git rev-parse HEAD 2>/dev/null || echo \`\`) > ${hash_file_path}`);
                }
            });
        });
    });
    return callback();
}

function cleanPlugins() {
    return del(["../static/plugins/{visualizations,interactive_environments}/*"], { force: true });
}

client = parallel(fonts, stageLibs);
plugins = series(buildPlugins, cleanPlugins, stagePlugins);

module.exports.client = client;
module.exports.plugins = plugins;

module.exports.default = parallel(client, plugins);
