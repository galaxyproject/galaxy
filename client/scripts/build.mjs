#!/usr/bin/env node
/**
 * Galaxy client build script
 *
 * Usage:
 *   node scripts/build.mjs           # Run both icons and plugins (parallel)
 *   node scripts/build.mjs icons     # Build icons only
 *   node scripts/build.mjs plugins   # Install/stage plugins only
 *   node scripts/build.mjs plugins --force  # Force reinstall plugins
 */
import path from "node:path";
import fs from "fs-extra";
import { execSync } from "node:child_process";
import { globSync } from "glob";
import { parse as parseYaml } from "yaml";
import os from "node:os";
import { fileURLToPath } from "node:url";

import { buildIcons } from "../icons/build_icons.mjs";
import { generateIconsTypeScript } from "../icons/generate_ts_icons.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const clientDir = path.resolve(__dirname, "..");

// Check if visualization steps should be skipped
const SKIP_VIZ = process.env.SKIP_VIZ === "true" || process.env.SKIP_VIZ === "1";

const pluginBaseDir =
    (process.env.GALAXY_PLUGIN_PATH && process.env.GALAXY_PLUGIN_PATH !== "None"
        ? process.env.GALAXY_PLUGIN_PATH
        : undefined) || path.join(clientDir, "../config/plugins/");

const staticPluginDir = path.join(clientDir, "../static/plugins");
const visualizationsConfig = path.join(clientDir, "visualizations.yml");

// Load visualization config
let VISUALIZATION_PLUGINS = {};
try {
    if (fs.existsSync(visualizationsConfig)) {
        const file = fs.readFileSync(visualizationsConfig, "utf8");
        VISUALIZATION_PLUGINS = parseYaml(file) || {};
    } else {
        console.warn(`Visualization config file not found: ${visualizationsConfig}`);
    }
} catch (err) {
    console.error(`Error loading visualization config: ${err.message}`);
    VISUALIZATION_PLUGINS = {};
}

async function icons() {
    console.log("Building icons...");
    await buildIcons(path.join(clientDir, "src/assets/icons.json"));
    generateIconsTypeScript();
    console.log("Icons build complete.");
}

async function cleanPlugins() {
    if (SKIP_VIZ) {
        console.log("Skipping plugin cleanup (SKIP_VIZ is set)");
        return;
    }

    const vizStagingDir = path.join(staticPluginDir, "visualizations");
    console.log(`Cleaning visualization staging directory: ${vizStagingDir}`);
    fs.removeSync(vizStagingDir);
}

async function stagePlugins() {
    if (SKIP_VIZ) {
        console.log("Skipping plugin staging (SKIP_VIZ is set)");
        return;
    }

    fs.ensureDirSync(path.join(staticPluginDir, "visualizations"));

    // Get visualization directories
    const visualizationDirs = path.join(pluginBaseDir, "visualizations/*/static");
    const dirs = globSync(visualizationDirs);

    // Process each directory
    const copyPromises = dirs.map(async (sourceDir) => {
        // Get the relative path from the plugin base dir
        const relativeDir = path.relative(pluginBaseDir, sourceDir);

        // Extract the plugin name from the path for logging
        const pathParts = relativeDir.split(path.sep);
        const pluginName = pathParts[1]; // visualizations/[pluginName]/static

        console.log(`Staging plugin '${pluginName}' from ${sourceDir}`);

        // The target should preserve the full path including 'static'
        const targetDir = path.join(staticPluginDir, relativeDir);

        // Skip node_modules/.bin directories
        if (sourceDir.includes("node_modules/.bin")) {
            return;
        }

        try {
            await fs.copy(sourceDir, targetDir, {
                filter: (src) => !src.includes("node_modules/.bin"),
            });
        } catch (err) {
            console.error(`Error copying ${sourceDir}:`, err);
            // Don't fail the entire build for a single plugin
        }
    });

    await Promise.all(copyPromises);
    console.log("Plugin staging completed successfully");
}

async function installVisualizations(forceReinstall = false) {
    if (SKIP_VIZ) {
        console.log("Skipping visualization installation (SKIP_VIZ is set)");
        return;
    }

    const visualizationsDir = path.join(pluginBaseDir, "visualizations");
    fs.ensureDirSync(visualizationsDir);

    for (const pluginName of Object.keys(VISUALIZATION_PLUGINS)) {
        const pluginConfig = VISUALIZATION_PLUGINS[pluginName];

        // Validate plugin configuration
        if (!pluginConfig.package || !pluginConfig.version) {
            console.error(`Invalid configuration for plugin '${pluginName}': missing package or version`);
            continue;
        }

        const { package: pluginPackage, version } = pluginConfig;
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
            execSync(`npm install ${currentHash}`, {
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
}

async function plugins(forceReinstall = false) {
    console.log("Processing visualization plugins...");
    await installVisualizations(forceReinstall);
    await cleanPlugins();
    await stagePlugins();
    console.log("Plugin processing complete.");
}

async function main() {
    const args = process.argv.slice(2);
    const forceReinstall = args.includes("--force");
    const tasks = args.filter((arg) => !arg.startsWith("--"));

    // If no tasks specified, run both in parallel
    if (tasks.length === 0) {
        console.log("Running all build tasks...");
        await Promise.all([icons(), plugins(forceReinstall)]);
        console.log("All build tasks complete.");
        return;
    }

    // Run specified tasks
    for (const task of tasks) {
        switch (task) {
            case "icons":
                await icons();
                break;
            case "plugins":
                await plugins(forceReinstall);
                break;
            default:
                console.error(`Unknown task: ${task}`);
                console.error("Available tasks: icons, plugins");
                process.exit(1);
        }
    }
}

main().catch((err) => {
    console.error("Build failed:", err);
    process.exit(1);
});
