const path = require("path");
const fs = require("fs-extra");
const del = require("del");
const { parallel, series } = require("gulp");
const child_process = require("child_process");
const { globSync } = require("glob");
const buildIcons = require("./icons/build_icons");
const os = require("os");
const yaml = require("yaml");

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

const staticPluginDir = "../static/plugins";
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
    fs.ensureDirSync(path.join(staticPluginDir));

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
        const targetDir = path.join(staticPluginDir, relativeDir);

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

/**
 * Produce plugins from fully self-contained npm packages
 */
async function installVisualizations(callback, forceReinstall = false) {
    const visualizationsDir = path.join(PATHS.pluginBaseDir, "visualizations");
    fs.ensureDirSync(visualizationsDir);
    for (const pluginName of Object.keys(VISUALIZATION_PLUGINS)) {
        const { package: pluginPackage, version } = VISUALIZATION_PLUGINS[pluginName];
        const pluginDir = path.join(visualizationsDir, pluginName);
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

function forceInstallVisualizations(callback) {
    return installVisualizations(callback, true);
}

const client = parallel(stageLibs, icons);
const plugins = series(installVisualizations, stagePlugins);
const pluginsRebuild = series(forceInstallVisualizations, stagePlugins);

module.exports.client = client;
module.exports.plugins = plugins;
module.exports.default = parallel(client, plugins);
module.exports.installVisualizations = installVisualizations;
module.exports.pluginsRebuild = pluginsRebuild;
