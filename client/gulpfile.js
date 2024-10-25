const path = require("path");
const fs = require("fs-extra");
const del = require("del");
const { src, dest, series, parallel, watch } = require("gulp");
const child_process = require("child_process");
const { globSync } = require("glob");
const buildIcons = require("./icons/build_icons");
const xml2js = require("xml2js");

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
    "fits_image_viewer",
    "h5web",
    "heatmap/heatmap_default",
    "hyphyvision",
    "jqplot/jqplot_bar",
    "media_player",
    "mvpapp",
    "nora",
    "nvd3/nvd3_bar",
    "openseadragon",
    "PCA_3Dplot",
    "phylocanvas",
    "pv",
    "scatterplot",
    "tiffviewer",
    "ts_visjs",
    "venn",
    "vizarr",
];
const INSTALL_PLUGIN_BUILD_IDS = ["ngl", "msa", "openlayers"]; // todo: derive from XML
const DIST_PLUGIN_BUILD_IDS = ["new_user"];
const PLUGIN_BUILD_IDS = Array.prototype.concat(DIST_PLUGIN_BUILD_IDS, STATIC_PLUGIN_BUILD_IDS);

const failOnError =
    process.env.GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR && process.env.GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR !== "0"
        ? true
        : false;

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

async function icons() {
    await buildIcons("./src/assets/icons.json");
}

function stagePlugins() {
    return src(PATHS.pluginDirs).pipe(dest("../static/plugins/"));
}

function buildPlugins(callback, forceRebuild) {
    /*
     * Walk pluginBuildModules glob and attempt to build modules.
     * */
    const packageJsons = globSync(PATHS.pluginBuildModules, {});
    packageJsons.forEach((file) => {
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
                const hashFileContent = fs.readFileSync(hashFilePath, "utf8").trim();
                const isHash = /^[0-9a-f]{7,40}$/.test(hashFileContent); // Check for a 7 to 40 character hexadecimal string

                if (!isHash) {
                    console.log(`Hash file for ${pluginName} exists but does not have a valid git hash.`);
                    skipBuild = false;
                } else {
                    skipBuild =
                        child_process.spawnSync("git", ["diff", "--quiet", hashFileContent, "--", pluginDir], {
                            stdio: "inherit",
                            shell: true,
                        }).status === 0;
                }

                skipBuild =
                    child_process.spawnSync("git", ["diff", "--quiet", `$(cat ${hashFilePath})`, "--", pluginDir], {
                        stdio: "inherit",
                        shell: true,
                    }).status === 0;
                if (!skipBuild) {
                    // Hash exists and is outdated, triggering a rebuild.
                    // Stage current hash to .orig for debugging and to
                    // force a plugin rebuild in the event of a failure
                    // (i.e. -- we're committed to a new build of this plugin).
                    fs.renameSync(hashFilePath, `${hashFilePath}.orig`);
                }
            } else {
                console.log(`No build hashfile detected for ${pluginName}, generating now.`);
            }
        }

        if (skipBuild) {
            console.log(`No changes detected for ${pluginName}`);
        } else {
            console.log(`Installing Dependencies for ${pluginName}`);

            // Else we call yarn install and yarn build
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
            const opts = {
                cwd: pluginDir,
                stdio: "inherit",
                shell: true,
            };
            // if node version is >16, set NODE_OPTIONS to use legacy openssl provider
            if (process.versions.node.split(".")[0] > "16") {
                opts.env = {
                    ...process.env,
                    PARCEL_WORKER_BACKEND: "process",
                    NODE_OPTIONS: "--openssl-legacy-provider",
                };
            }
            if (child_process.spawnSync("yarn", ["build"], opts).status === 0) {
                console.log(`Successfully built, saving build state to ${hashFilePath}`);
                child_process.exec(`(git rev-parse HEAD 2>/dev/null || echo \`\`) > ${hashFilePath}`);
            } else {
                console.error(
                    `Error building ${pluginName}, not saving build state.  Please report this issue to the Galaxy Team.`
                );
                if (failOnError) {
                    // Fail on error.
                    console.error(
                        "Failing build due to GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR being set, see error(s) above."
                    );
                    process.exit(1);
                }
            }
        }
    });
    return callback();
}

async function installPlugins(callback) {
    // iterate through install_plugin_build_ids, identify xml files and install dependencies
    for (const plugin_name of INSTALL_PLUGIN_BUILD_IDS) {
        const pluginDir = path.join(PATHS.pluginBaseDir, `visualizations/${plugin_name}`);
        const xmlPath = path.join(pluginDir, `config/${plugin_name}.xml`);
        // Check if the file exists
        if (fs.existsSync(xmlPath)) {
            await installDependenciesFromXML(xmlPath, pluginDir);
        } else {
            console.error(`XML file not found: ${xmlPath}`);
        }
    }
    return callback();
}

// Function to parse the XML and install dependencies
async function installDependenciesFromXML(xmlPath, pluginDir) {
    try {
        const pluginXML = fs.readFileSync(xmlPath);
        const parsedXML = await xml2js.parseStringPromise(pluginXML);
        const requirements = parsedXML.visualization.requirements[0].requirement;

        const installPromises = requirements.map(async (dep) => {
            const { type: reqType, package: pkgName, version } = dep.$;

            if (reqType === "npm" && pkgName && version) {
                try {
                    const installResult = child_process.spawnSync(
                        "npm",
                        ["install", "--silent", "--no-save", "--prefix .", `${pkgName}@${version}`],
                        {
                            cwd: pluginDir,
                            stdio: "inherit",
                            shell: true,
                        }
                    );

                    if (installResult.status === 0) {
                        await fs.copy(
                            path.join(pluginDir, "node_modules", pkgName, "static"),
                            path.join(pluginDir, "static")
                        );
                        console.log(`Installed package ${pkgName}@${version} in ${pluginDir}`);
                    } else {
                        console.error(`Error installing package ${pkgName}@${version} in ${pluginDir}`);
                    }
                } catch (err) {
                    console.error(`Error handling package ${pkgName}@${version} in ${pluginDir}:`, err);
                }
            }
        });

        await Promise.all(installPromises);
    } catch (err) {
        console.error(`Error processing XML file ${xmlPath}:`, err);
    }
}

function forceBuildPlugins(callback) {
    return buildPlugins(callback, true);
}

function cleanPlugins() {
    return del(["../static/plugins/{visualizations,welcome_page}/*"], { force: true });
}

const client = parallel(fonts, stageLibs, icons);
const plugins = series(buildPlugins, installPlugins, cleanPlugins, stagePlugins);
const pluginsRebuild = series(forceBuildPlugins, installPlugins, cleanPlugins, stagePlugins);

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
module.exports.installPlugins = installPlugins;
