#!/usr/bin/env node

/**
 * Galaxy Client API Version Synchronization Script
 *
 * Reads Galaxy's version.py and updates package.json with a semver-compatible version.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Get directory paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const galaxyRoot = process.env.GALAXY_ROOT || path.resolve(__dirname, "../..");
const clientApiRoot = path.resolve(__dirname, "..");

// File paths
const galaxyVersionPath = path.join(galaxyRoot, "lib/galaxy/version.py");
const packageJsonPath = path.join(clientApiRoot, "package.json");

// Check if Galaxy version.py exists
if (!fs.existsSync(galaxyVersionPath)) {
    console.error(`Galaxy version file not found at ${galaxyVersionPath}`);
    process.exit(1);
}

// Read Galaxy version information
const versionPy = fs.readFileSync(galaxyVersionPath, "utf-8");
const majorMatch = versionPy.match(/VERSION_MAJOR\s*=\s*"([^"]+)"/);
const minorMatch = versionPy.match(/VERSION_MINOR\s*=\s*"([^"]+)"/);

if (!majorMatch) {
    console.error("Could not find VERSION_MAJOR in version.py");
    process.exit(1);
}

// Parse Galaxy version components
const galaxyMajor = majorMatch[1].split(".")[0];
const galaxyMinor = majorMatch[1].split(".")[1] || "0";
const preRelease = minorMatch && minorMatch[1] ? minorMatch[1] : null;

// Read current package.json
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));
const currentVersion = packageJson.version;

// Create npm-compatible version
let newVersion;

if (preRelease) {
    // Handle prerelease versions (dev0, rc1, etc.)
    const type = preRelease.match(/^([a-z]+)/)[1]; // dev, rc, etc.
    const num = preRelease.match(/\d+$/)[0]; // The trailing number
    newVersion = `${galaxyMajor}.${galaxyMinor}.0-${type}.${num}`;
} else {
    // Stable release
    newVersion = `${galaxyMajor}.${galaxyMinor}.0`;
}

// Update if different
if (currentVersion !== newVersion) {
    console.log(`Updating version from ${currentVersion} to ${newVersion}`);

    packageJson.version = newVersion;
    fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + "\n", "utf-8");

    console.log("Version updated successfully");
} else {
    console.log(`Version is already up to date (${currentVersion})`);
}
