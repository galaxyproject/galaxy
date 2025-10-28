#!/usr/bin/env node

/**
 * Helper script to migrate a test file from Jest to Vitest
 * Usage: node scripts/migrate-to-vitest.js <test-file-path>
 */

const fs = require("fs");
const path = require("path");

function migrateTestFile(filePath) {
    if (!fs.existsSync(filePath)) {
        console.error(`File not found: ${filePath}`);
        process.exit(1);
    }

    // Read the file
    let content = fs.readFileSync(filePath, "utf8");
    
    // Create the new filename
    const dir = path.dirname(filePath);
    const basename = path.basename(filePath);
    const newBasename = basename.replace(/\.test\.(js|ts)$/, ".vitest.test.$1");
    const newFilePath = path.join(dir, newBasename);
    
    // Check if already migrated
    if (fs.existsSync(newFilePath)) {
        console.error(`Vitest file already exists: ${newFilePath}`);
        process.exit(1);
    }

    console.log(`Migrating ${filePath} to ${newFilePath}`);

    // Common replacements
    const replacements = [
        // Update test helper imports
        [/@tests\/jest\/helpers/g, "@tests/vitest/helpers"],
        
        // Add vitest imports if not present
        [/^(import .* from ['"]@vue\/test-utils['"];?)$/m, (match) => {
            if (!content.includes("from \"vitest\"")) {
                return match + "\nimport { describe, it, expect, beforeEach, afterEach, vi } from \"vitest\";";
            }
            return match;
        }],
        
        // Replace jest with vi
        [/\bjest\.fn\(/g, "vi.fn("],
        [/\bjest\.spyOn\(/g, "vi.spyOn("],
        [/\bjest\.mock\(/g, "vi.mock("],
        [/\bjest\.doMock\(/g, "vi.doMock("],
        [/\bjest\.mocked\(/g, "vi.mocked("],
        [/\bjest\.useFakeTimers\(/g, "vi.useFakeTimers("],
        [/\bjest\.useRealTimers\(/g, "vi.useRealTimers("],
        [/\bjest\.clearAllMocks\(/g, "vi.clearAllMocks("],
        [/\bjest\.resetAllMocks\(/g, "vi.resetAllMocks("],
        [/\bjest\.restoreAllMocks\(/g, "vi.restoreAllMocks("],
        
        // Handle module mocking at top level
        [/^(jest\.mock\(.+\);?)$/gm, (match) => {
            console.log(`  ⚠️  Found module mock that may need manual review: ${match}`);
            return match.replace("jest.mock", "vi.mock");
        }],
    ];

    // Apply replacements
    for (const [pattern, replacement] of replacements) {
        content = content.replace(pattern, replacement);
    }

    // Write the new file
    fs.writeFileSync(newFilePath, content);
    console.log(`✅ Created ${newFilePath}`);

    // Update migration tracker
    const trackerPath = path.join(process.cwd(), ".vitest-migrated.json");
    let tracker = { migrated: [], notes: {} };
    
    if (fs.existsSync(trackerPath)) {
        tracker = JSON.parse(fs.readFileSync(trackerPath, "utf8"));
    }
    
    const relativePath = path.relative(process.cwd(), newFilePath).replace(/\\/g, "/");
    const originalRelativePath = path.relative(process.cwd(), filePath).replace(/\\/g, "/");
    
    if (!tracker.migrated.includes(relativePath)) {
        tracker.migrated.push(relativePath);
        tracker.lastUpdated = new Date().toISOString().split("T")[0];
        tracker.notes[relativePath] = {
            originalFile: originalRelativePath,
            migratedDate: new Date().toISOString().split("T")[0],
            changes: "Automated migration with jest->vi replacements",
        };
        
        fs.writeFileSync(trackerPath, JSON.stringify(tracker, null, 2) + "\n");
        console.log("✅ Updated .vitest-migrated.json");
    }

    console.log("\n📋 Next steps:");
    console.log(`1. Review the migrated file: ${newFilePath}`);
    console.log(`2. Run the test with: yarn test:vitest:run ${relativePath}`);
    console.log(`3. If the test passes, you can remove the original file: ${filePath}`);
    console.log("\n⚠️  Manual review may be needed for:");
    console.log("   - Complex mocking patterns");
    console.log("   - Timer usage");
    console.log("   - Snapshot tests");
    console.log("   - Custom matchers");
}

// Main execution
const args = process.argv.slice(2);
if (args.length === 0) {
    console.error("Usage: node scripts/migrate-to-vitest.js <test-file-path>");
    process.exit(1);
}

const testFile = args[0];
migrateTestFile(testFile);