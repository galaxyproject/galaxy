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
    "PCA_3Dplot",
    "pv",
    "nora",
    "venn",
];
const DIST_PLUGIN_BUILD_IDS = ["new_user"];
const PLUGIN_BUILD_IDS = Array.prototype.concat(DIST_PLUGIN_BUILD_IDS, STATIC_PLUGIN_BUILD_IDS);

const PATHS = {
    nodeModules: "./node_modules",
    stagedLibraries: {
        // This is a stepping stone towards having all this staged
        // automatically.  Eventually, this dictionary and staging step will
        // not be necessary.
        backbone: ["backbone.js", "backbone.js"],
        jquery: ["dist/jquery.js", "jquery/jquery.js"],
        "jquery-migrate": ["dist/jquery-migrate.js", "jquery/jquery.migrate.js"],
        "jquery-mousewheel": ["jquery.mousewheel.js", "jquery/jquery.mousewheel.js"],
        requirejs: ["require.js", "require.js"],
        underscore: ["underscore.js", "underscore.js"],
    },
};

PATHS.pluginBaseDir =
    (process.env.GALAXY_PLUGIN_PATH && process.env.GALAXY_PLUGIN_PATH !== "None"
        ? process.env.GALAXY_PLUGIN_PATH
        : undefined) || "../config/plugins/";

PATHS.pluginDirs = [
    path.join(PATHS.pluginBaseDir, "{visualizations,welcome_page}/*/static/**/*"),
    path.join(PATHS.pluginBaseDir, "{visualizations,welcome_page}/*/*/static/**/*"),
];

PATHS.pluginBuildModules = [
    path.join(PATHS.pluginBaseDir, `{visualizations,welcome_page}/{${PLUGIN_BUILD_IDS.join(",")}}/package.json`),
];

function stageLibs(callback) {
    Object.keys(PATHS.stagedLibraries).forEach((lib) => {
        var p1 = path.resolve(path.join(PATHS.nodeModules, lib, PATHS.stagedLibraries[lib][0]));
        var p2 = path.resolve(path.join("src", "libs", PATHS.stagedLibraries[lib][1]));
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
    return src(path.resolve(path.join(PATHS.nodeModules, "font-awesome/fonts/**/*"))).pipe(
        dest("../static/images/fonts")
    );
}

function stagePlugins() {
    return src(PATHS.pluginDirs).pipe(dest("../static/plugins/"));
}

function buildPlugins(callback, forceRebuild) {
    /*
     * Walk pluginBuildModules glob and attempt to build modules.
     * */
    PATHS.pluginBuildModules.map((buildModule) => {
        glob(buildModule, {}, (er, files) => {
            files.map((file) => {
                let skipBuild = false;
                const pluginDir = path.dirname(file);
                const pluginName = pluginDir.split(path.sep).pop();

                const hashFilePath = path.join(
                    pluginDir,
                    DIST_PLUGIN_BUILD_IDS.indexOf(pluginName) > -1 ? "dist" : "static",
                    "plugin_build_hash.txt"
                );

                if (forceRebuild) {
                    skipBuild = false;
                } else {
                    if (fs.existsSync(hashFilePath)) {
                        skipBuild =
                            child_process.spawnSync(
                                "git",
                                ["diff", "--quiet", `$(cat ${hashFilePath})`, "--", pluginDir],
                                {
                                    stdio: "inherit",
                                    shell: true,
                                }
                            ).status === 0;
                    } else {
                        console.log(`No build hashfile detected for ${pluginName}, generating now.`);
                    }
                }

                if (skipBuild) {
                    console.log(`No changes detected for ${pluginName}`);
                } else {
                    console.log(`Installing Dependencies for ${pluginName}`);
                    child_process.spawnSync(
                        "yarn",
                        ["install", "--production=false", "--network-timeout=300000", "--check-files"],
                        {
                            cwd: pluginDir,
                            stdio: "inherit",
                            shell: true,
                        }
                    );
                    console.log(`Building ${pluginName}`);
                    if (
                        child_process.spawnSync("yarn", ["build"], { cwd: pluginDir, stdio: "inherit", shell: true })
                            .status === 0
                    ) {
                        console.log(`Successfully built, saving build state to ${hashFilePath}`);
                        child_process.exec(`(git rev-parse HEAD 2>/dev/null || echo \`\`) > ${hashFilePath}`);
                    } else {
                        console.error(
                            `Error building ${pluginName}, not saving build state.  Please report this issue to the Galaxy Team.`
                        );
                    }
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
    return del(["../static/plugins/{visualizations,welcome_page}/*"], { force: true });
}

const client = parallel(fonts, stageLibs);
const plugins = series(buildPlugins, cleanPlugins, stagePlugins);
const pluginsRebuild = series(forceBuildPlugins, cleanPlugins, stagePlugins);

function watchPlugins() {
    const BUILD_PLUGIN_WATCH_GLOB = [
        path.join(PATHS.pluginBaseDir, `{visualizations,welcome_page}/{${PLUGIN_BUILD_IDS.join(",")}}/**/*`),
    ];
    watch(BUILD_PLUGIN_WATCH_GLOB, { queue: false }, plugins);
}

module.exports.client = client;
module.exports.plugins = plugins;
module.exports.pluginsRebuild = pluginsRebuild;
module.exports.watchPlugins = watchPlugins;
module.exports.default = parallel(client, plugins);
