const path = require("path");
const fs = require("fs");
const del = require("del");
const { src, dest, series, parallel, watch } = require("gulp");
const child_process = require("child_process");
const glob = require("glob");

/*
 * We'll want a flexible glob down the road, but for now there are no
 * un-built visualizations in the repository; for performance and
 * simplicity just add them one at a time until we upgrade older viz's.
 */
const STATIC_PLUGIN_BUILD_IDS = [
    "annotate_image",
    "chiraviz",
    "cytoscape",
    "drawrna",
    "editor",
    "example",
    "heatmap/heatmap_default",
    "hyphyvision",
    "jqplot/jqplot_bar",
    "media_player",
    "mvpapp",
    "ngl",
    "nvd3/nvd3_bar",
    "openlayers",
    "openseadragon",
    "pv",
    "nora",
    "venn",
];

const DIST_PLUGIN_BUILD_IDS = ["new_user"];

const PLUGIN_BUILD_IDS = Array.prototype.concat(DIST_PLUGIN_BUILD_IDS, STATIC_PLUGIN_BUILD_IDS);

const paths = {
    node_modules: "./node_modules",
    plugin_dirs: [
        "../config/plugins/{visualizations,interactive_environments,welcome_page}/*/static/**/*",
        "../config/plugins/{visualizations,interactive_environments,welcome_page}/*/*/static/**/*",
    ],
    plugin_build_modules: [
        `../config/plugins/{visualizations,welcome_page}/{${PLUGIN_BUILD_IDS.join(",")}}/package.json`,
    ],
    lib_locs: {
        // This is a stepping stone towards having all this staged
        // automatically.  Eventually, this dictionary and staging step will
        // not be necessary.
        backbone: ["backbone.js", "backbone.js"],
        "@galaxyproject/bootstrap-tour": ["build/js/bootstrap-tour.js", "bootstrap-tour.js"],
        jquery: ["dist/jquery.js", "jquery/jquery.js"],
        "jquery.cookie": ["jquery.cookie.js", "jquery/jquery.cookie.js"],
        "jquery-migrate": ["dist/jquery-migrate.js", "jquery/jquery.migrate.js"],
        "jquery-mousewheel": ["jquery.mousewheel.js", "jquery/jquery.mousewheel.js"],
        requirejs: ["require.js", "require.js"],
        underscore: ["underscore.js", "underscore.js"],
    },
    libs: ["src/libs/**/*.js"],
};

function stageLibs(callback) {
    Object.keys(paths.lib_locs).forEach((lib) => {
        var p1 = path.resolve(path.join(paths.node_modules, lib, paths.lib_locs[lib][0]));
        var p2 = path.resolve(path.join("src", "libs", paths.lib_locs[lib][1]));
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

function buildPlugins(callback, forceRebuild) {
    /*
     * Walk plugin_build_modules glob and attempt to build modules.
     * */
    paths.plugin_build_modules.map((build_module) => {
        glob(build_module, {}, (er, files) => {
            files.map((file) => {
                let skipBuild = false;
                const f = path.join(process.cwd(), file).slice(0, -12);
                const plugin_name = path.dirname(file).split(path.sep).pop();
                const hash_file_path = path.join(
                    f,
                    DIST_PLUGIN_BUILD_IDS.indexOf(plugin_name) > -1 ? "dist" : "static",
                    "plugin_build_hash.txt"
                );

                if (!!forceRebuild) {
                    skipBuild = false;
                } else {
                    if (fs.existsSync(hash_file_path)) {
                        skipBuild =
                            child_process.spawnSync("git", ["diff", "--quiet", `$(cat ${hash_file_path})`, "--", f], {
                                stdio: "inherit",
                                shell: true,
                            }).status === 0;
                    } else {
                        console.log(`No build hashfile detected for ${plugin_name}, generating now.`);
                    }
                }

                if (skipBuild) {
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

function forceBuildPlugins(callback) {
    return buildPlugins(callback, true);
}

function cleanPlugins() {
    return del(["../static/plugins/{visualizations,interactive_environments,welcome_page}/*"], { force: true });
}

const client = parallel(fonts, stageLibs);
const plugins = series(buildPlugins, cleanPlugins, stagePlugins);
const pluginsRebuild = series(forceBuildPlugins, cleanPlugins, stagePlugins);

function watchPlugins() {
    const BUILD_PLUGIN_WATCH_GLOB = [
        `../config/plugins/{visualizations,welcome_page}/{${PLUGIN_BUILD_IDS.join(",")}}/**/*`,
    ];
    watch(BUILD_PLUGIN_WATCH_GLOB, { queue: false }, plugins);
}

module.exports.client = client;
module.exports.plugins = plugins;
module.exports.pluginsRebuild = pluginsRebuild;
module.exports.watchPlugins = watchPlugins;
module.exports.default = parallel(client, plugins);
