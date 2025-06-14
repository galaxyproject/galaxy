const path = require("path");
const fs = require("fs-extra");
const del = require("del");
const { series, parallel, watch } = require("gulp");
const child_process = require("child_process");
const { globSync } = require("glob");
const buildIcons = require("./icons/build_icons");
const os = require("os");
const yaml = require("yaml");

/*
 * We'll want a flexible glob down the road, but for now there are no
 * un-built visualizations in the repository; for performance and
 * simplicity just add them one at a time until we upgrade older viz's.
 */
const PLUGIN_BUILD_IDS = ["hyphyvision"];

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

const visualizationsConfig = "./visualizations.yml";
const file = fs.readFileSync(visualizationsConfig, "utf8");
const VISUALIZATION_PLUGINS = yaml.parse(file);

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
 * Produce plugins from fully self-contained npm packages
 */
async function installVisualizations(callback, forceReinstall = false) {
    for (const pluginName of Object.keys(VISUALIZATION_PLUGINS)) {
        const { package: pluginPackage, version } = VISUALIZATION_PLUGINS[pluginName];
        const pluginDir = path.join(PATHS.pluginBaseDir, `visualizations/${pluginName}`);
        const staticDir = path.join(pluginDir, "static");
        const xmlPath = path.join(staticDir, `${pluginName}.xml`);
        const hashFilePath = path.join(staticDir, "plugin_build_hash.txt");
        const currentHash = `${pluginPackage}@${version}`;
        let tempDir = null;
        try {
            if (!forceReinstall && fs.existsSync(hashFilePath)) {
                const storedHash = fs.readFileSync(hashFilePath, "utf8").trim();
                if (storedHash === currentHash) {
                    console.log(`Package ${currentHash} already installed for ${pluginName}, skipping.`);
                    continue;
                }
            }
            console.log(`Installing ${currentHash} into ${pluginDir}...`);
            tempDir = fs.mkdtempSync(path.join(os.tmpdir(), `${pluginName}-`));
            fs.writeFileSync(path.join(tempDir, "package.json"), JSON.stringify({ private: true }, null, 2));
            child_process.execSync(`npm install ${currentHash}`, {
                cwd: tempDir,
                stdio: "pipe",
                shell: true,
            });
            const pkgDir = path.join(tempDir, "node_modules", pluginPackage);
            if (!fs.existsSync(pkgDir)) {
                throw new Error(`Package directory not found: ${pkgDir}`);
            }
            fs.emptyDirSync(pluginDir);
            fs.copySync(pkgDir, pluginDir, { overwrite: true });
            if (!fs.existsSync(xmlPath)) {
                throw new Error(`Expected XML file not found after install: ${xmlPath}`);
            }
            fs.writeFileSync(hashFilePath, currentHash);
            console.log(`Installed ${currentHash} into ${pluginDir}`);
        } catch (err) {
            console.error(`Failed to install ${pluginPackage}@${version} for ${pluginName}:`, err);
        } finally {
            if (tempDir && fs.existsSync(tempDir)) {
                try {
                    fs.removeSync(tempDir);
                } catch (cleanupErr) {
                    console.warn(`Warning: Failed to clean temp dir ${tempDir}:`, cleanupErr);
                }
            }
        }
    }
    return callback();
}

function forceBuildPlugins(callback) {
    return buildPlugins(callback, true);
}

function forceInstallVisualizations(callback) {
    return installVisualizations(callback, true);
}

function cleanPlugins() {
    return del(["../static/plugins/visualizations/*"], { force: true });
}

const client = parallel(stageLibs, icons);
const plugins = series(buildPlugins, installVisualizations, cleanPlugins, stagePlugins);
const pluginsRebuild = series(forceBuildPlugins, forceInstallVisualizations, cleanPlugins, stagePlugins);

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
module.exports.installVisualizations = installVisualizations;
