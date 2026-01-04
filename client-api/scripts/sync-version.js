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
// VERSION_MAJOR is like "25.0" or "25.1"
const [galaxyMajor, galaxyMinor] = majorMatch[1].split(".");
const versionMinor = minorMatch && minorMatch[1] ? minorMatch[1] : "";

// Read current package.json
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));
const currentVersion = packageJson.version;

// Create npm-compatible version
// VERSION_MINOR can be:
//   - "" or "0" → stable initial release (25.0.0)
//   - "4" → stable patch release (25.0.4)
//   - "dev0" → prerelease (25.0.0-dev.0)
//   - "5.dev0" → patch prerelease (25.0.5-dev.0)
let newVersion;

if (!versionMinor || versionMinor === "0") {
    // Initial stable release
    newVersion = `${galaxyMajor}.${galaxyMinor}.0`;
} else if (/^\d+$/.test(versionMinor)) {
    // Stable patch release (just a number like "4")
    newVersion = `${galaxyMajor}.${galaxyMinor}.${versionMinor}`;
} else if (/^\d+\./.test(versionMinor)) {
    // Patch prerelease like "5.dev0" → 25.0.5-dev.0
    const [patch, prerelease] = versionMinor.split(".");
    const type = prerelease.match(/^([a-z]+)/)[1];
    const num = prerelease.match(/\d+$/)[0];
    newVersion = `${galaxyMajor}.${galaxyMinor}.${patch}-${type}.${num}`;
} else {
    // Initial prerelease like "dev0" or "rc1" → 25.0.0-dev.0
    const type = versionMinor.match(/^([a-z]+)/)[1];
    const num = versionMinor.match(/\d+$/)[0];
    newVersion = `${galaxyMajor}.${galaxyMinor}.0-${type}.${num}`;
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
