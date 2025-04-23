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
const PLUGIN_BUILD_IDS = [
    "annotate_image",
    "chiraviz",
    "drawrna",
    "editor",
    "example",
    "fits_graph_viewer",
    "fits_image_viewer",
    "hyphyvision",
    "jqplot/jqplot_bar",
    "media_player",
    "mvpapp",
    "nora",
    "nvd3/nvd3_bar",
    "openseadragon",
    "PCA_3Dplot",
    "pv",
    "scatterplot",
    "tiffviewer",
    "ts_visjs",
];
const INSTALL_PLUGIN_BUILD_IDS = [
    "cytoscape",
    "h5web",
    "heatmap",
    "ngl",
    "msa",
    "openlayers",
    "phylocanvas",
    "plotly",
    "venn",
    "vitessce",
    "vizarr",
]; // todo: derive from XML

const args = process.argv.slice(2);
const limitIndex = args.indexOf("--limit");
const pluginFilter = limitIndex !== -1 && args[limitIndex + 1] ? args[limitIndex + 1] : "";

const applyPluginFilter = (plugin) => {
    return !pluginFilter || plugin.includes(pluginFilter);
};

const failOnError =
    process.env.GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR && process.env.GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR !== "0"
        ? true
        : false;

const PATHS = {
    nodeModules: "./node_modules",
    stagedLibraries: {
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
    path.join(PATHS.pluginBaseDir, "visualizations/*/static/**/*"),
    path.join(PATHS.pluginBaseDir, "visualizations/*/*/static/**/*"),
];

PATHS.pluginBuildModules = [
    ...PLUGIN_BUILD_IDS.filter(applyPluginFilter).map((plugin) =>
        path.join(PATHS.pluginBaseDir, `visualizations/${plugin}/package.json`)
    ),
];

function stageLibs(callback) {
    Object.keys(PATHS.stagedLibraries).forEach((lib) => {
        const p1 = path.resolve(path.join(PATHS.nodeModules, lib, PATHS.stagedLibraries[lib][0]));
        const p2 = path.resolve(path.join("src", "libs", PATHS.stagedLibraries[lib][1]));
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

async function icons() {
    await buildIcons("./src/assets/icons.json");
}

function stagePlugins(callback) {
    // Get visualization directories
    const visualizationDirs = [
        path.join(PATHS.pluginBaseDir, "visualizations/*/static"),
        path.join(PATHS.pluginBaseDir, "visualizations/*/*/static"),
    ];

    // Flatten the glob patterns to actual directory paths
    const dirs = [...globSync(visualizationDirs)];

    // Process each directory
    const copyPromises = dirs.map((sourceDir) => {
        // Get the relative path from the plugin base dir
        const relativeDir = path.relative(PATHS.pluginBaseDir, sourceDir);
        // The target should preserve the full path including 'static'
        const targetDir = path.join("../static/plugins", relativeDir);

        // Skip node_modules/.bin directories
        if (sourceDir.includes("node_modules/.bin")) {
            return Promise.resolve();
        }

        return fs
            .copy(sourceDir, targetDir, {
                filter: (src) => !src.includes("node_modules/.bin"),
            })
            .catch((err) => {
                console.error(`Error copying ${sourceDir}:`, err);
                // Don't fail the entire build for a single plugin
                return Promise.resolve();
            });
    });

    Promise.all(copyPromises)
        .then(() => {
            console.log("Plugin staging completed successfully");
            callback();
        })
        .catch((err) => {
            console.error("Error during plugin staging:", err);
            callback(err);
        });
}

function buildPlugins(callback, forceRebuild) {
    /*
     * Walk pluginBuildModules glob and attempt to build modules.
     */
    const packageJsons = globSync(PATHS.pluginBuildModules, {});
    packageJsons.forEach((file) => {
        let skipBuild = false;
        const pluginDir = path.dirname(file);
        const pluginName = pluginDir.split(path.sep).pop();

        const hashFilePath = path.join(pluginDir, "static", "plugin_build_hash.txt");

        if (forceRebuild) {
            skipBuild = false;
        } else {
            // Try reading existing plugin_build_hash.txt
            if (fs.existsSync(hashFilePath)) {
                const oldHash = fs.readFileSync(hashFilePath, "utf8").trim();
                const isHash = /^[0-9a-f]{7,40}$/.test(oldHash);

                if (!isHash) {
                    console.log(`Hash file for ${pluginName} exists but does not have a valid git hash.`);
                    skipBuild = false;
                } else {
                    // Check if there are changes since the stored hash
                    const diffResult = child_process.spawnSync("git", ["diff", "--quiet", oldHash, "--", pluginDir], {
                        stdio: "inherit",
                        shell: true,
                    });
                    skipBuild = diffResult.status === 0;
                    if (!skipBuild) {
                        // Hash exists and is outdated, rename to .orig
                        fs.renameSync(hashFilePath, `${hashFilePath}.orig`);
                    }
                }
            } else {
                console.log(`No build hashfile detected for ${pluginName}, generating now.`);
            }
        }

        if (skipBuild) {
            console.log(`No changes detected for ${pluginName}, skipping build.`);
        } else {
            console.log(`Installing Dependencies for ${pluginName}`);
            // Yarn install
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
            // Node >16 fix
            if (Number(process.versions.node.split(".")[0]) > 16) {
                opts.env = {
                    ...process.env,
                    PARCEL_WORKER_BACKEND: "process",
                    NODE_OPTIONS: "--openssl-legacy-provider",
                };
            }

            const buildResult = child_process.spawnSync("yarn", ["build"], opts);
            if (buildResult.status === 0) {
                console.log(`Successfully built, saving build state to ${hashFilePath}`);
                // Save new hash
                child_process.execSync(`git rev-parse HEAD > ${hashFilePath}`, {
                    stdio: "inherit",
                    shell: true,
                });
            } else {
                console.error(`Error building ${pluginName}, not saving build state.`);
                if (failOnError) {
                    console.error("Failing build due to GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR being set.");
                    process.exit(1);
                }
            }
        }
    });
    return callback();
}

/**
 * Same logic as buildPlugins, but for 'installed' plugins that rely on an XML
 * specifying npm dependencies (the INSTALL_PLUGIN_BUILD_IDS).
 */
async function installPlugins(callback, forceReinstall) {
    for (const pluginName of INSTALL_PLUGIN_BUILD_IDS.filter(applyPluginFilter)) {
        const pluginDir = path.join(PATHS.pluginBaseDir, `visualizations/${pluginName}`);
        const xmlPath = path.join(pluginDir, `config/${pluginName}.xml`);

        if (!fs.existsSync(xmlPath)) {
            console.error(`XML file not found: ${xmlPath}`);
            continue;
        }

        const hashFilePath = path.join(pluginDir, "static", "plugin_build_hash.txt");

        let skipInstall = false;
        if (!forceReinstall && fs.existsSync(hashFilePath)) {
            const oldHash = fs.readFileSync(hashFilePath, "utf8").trim();
            const isHash = /^[0-9a-f]{7,40}$/.test(oldHash);

            if (!isHash) {
                console.log(`Hash file for ${pluginName} exists but is not a valid git hash.`);
            } else {
                const diffResult = child_process.spawnSync("git", ["diff", "--quiet", oldHash, "--", pluginDir], {
                    stdio: "inherit",
                    shell: true,
                });
                skipInstall = diffResult.status === 0;
                if (!skipInstall) {
                    fs.renameSync(hashFilePath, `${hashFilePath}.orig`);
                }
            }
        } else if (!fs.existsSync(hashFilePath)) {
            console.log(`No install hashfile detected for ${pluginName}, generating now.`);
        }

        if (skipInstall) {
            console.log(`No changes detected for ${pluginName}, skipping re-installation.`);
        } else {
            console.log(`Installing npm dependencies for installed plugin ${pluginName}...`);
            try {
                await installDependenciesFromXML(xmlPath, pluginDir);
                console.log(`Finished installing for ${pluginName}, saving new hash.`);

                // Save the current commit hash
                child_process.execSync(`git rev-parse HEAD > ${hashFilePath}`, {
                    stdio: "inherit",
                    shell: true,
                });
            } catch (err) {
                console.error(`Error installing for ${pluginName}:`, err);
                if (failOnError) {
                    console.error(
                        "Failing build due to GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR being set, see error(s) above."
                    );
                    process.exit(1);
                }
            }
        }
    }
    return callback();
}

// Function to parse XML and install specified npm packages
async function installDependenciesFromXML(xmlPath, pluginDir) {
    const pluginXML = fs.readFileSync(xmlPath);
    const parsedXML = await xml2js.parseStringPromise(pluginXML);
    const requirements = parsedXML?.visualization?.requirements?.[0]?.requirement || [];

    // For each <requirement type="npm" package="xxx" version="yyy" />
    for (const dep of requirements) {
        const { type: reqType, package: pkgName, version } = dep.$;
        if (reqType === "npm" && pkgName && version) {
            console.log(`   → Installing ${pkgName}@${version} in ${pluginDir}`);
            const installResult = child_process.spawnSync(
                "npm",
                ["install", "--silent", "--no-save", `--prefix= .`, `${pkgName}@${version}`],
                {
                    cwd: pluginDir,
                    stdio: "inherit",
                    shell: true,
                }
            );

            if (installResult.status === 0) {
                // Installed successfully, copy over '/static' assets
                const potentialStaticPath = path.join(pluginDir, "node_modules", pkgName, "static");
                if (fs.existsSync(potentialStaticPath)) {
                    await fs.copy(potentialStaticPath, path.join(pluginDir, "static"));
                }
            } else {
                throw new Error(`npm install of ${pkgName}@${version} failed in ${pluginDir}`);
            }
        }
    }
}

function forceBuildPlugins(callback) {
    return buildPlugins(callback, true);
}

function forceInstallPlugins(callback) {
    return installPlugins(callback, true);
}

function cleanPlugins() {
    return del(["../static/plugins/visualizations/*"], { force: true });
}

const client = parallel(stageLibs, icons);
const plugins = series(buildPlugins, installPlugins, cleanPlugins, stagePlugins);
const pluginsRebuild = series(forceBuildPlugins, forceInstallPlugins, cleanPlugins, stagePlugins);

function watchPlugins() {
    const BUILD_PLUGIN_WATCH_GLOB = [
        path.join(PATHS.pluginBaseDir, `visualizations/{${PLUGIN_BUILD_IDS.join(",")}}/**/*`),
    ];
    watch(BUILD_PLUGIN_WATCH_GLOB, { queue: false }, plugins);
}

module.exports.client = client;
module.exports.plugins = plugins;
module.exports.pluginsRebuild = pluginsRebuild;
module.exports.watchPlugins = watchPlugins;
module.exports.default = parallel(client, plugins);
module.exports.installPlugins = installPlugins;
