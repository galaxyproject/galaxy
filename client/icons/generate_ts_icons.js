const fs = require("fs");
const path = require("path");

/**
 * Generate TypeScript exports for Galaxy custom icons
 * This converts the JSON icon definitions to proper IconDefinition objects
 * that can be imported directly, avoiding the need for string arrays
 */
function generateIconsTypeScript() {
    // Read the generated icons JSON
    const iconsJsonPath = path.resolve(__dirname, "../src/assets/icons.json");
    const outputPath = path.resolve(__dirname, "../src/components/icons/galaxyIcons.ts");

    if (!fs.existsSync(iconsJsonPath)) {
        console.error(`Icons JSON not found at ${iconsJsonPath}`);
        console.error("Run 'npm run icons' first to generate the icons JSON");
        return;
    }

    const iconsJson = fs.readFileSync(iconsJsonPath, "utf8");
    const icons = JSON.parse(iconsJson);

    // Generate TypeScript content
    let content = `import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

// Auto-generated Galaxy icons as IconDefinition objects
// This allows direct imports instead of using library registration and string arrays
// Generated from: ${iconsJsonPath}
// To regenerate, run: node icons/generate_ts_icons.js

`;

    icons.forEach((icon) => {
        // Convert icon name to camelCase for JavaScript export
        const exportName = icon.iconName;

        content += `export const ${exportName}: IconDefinition = ${JSON.stringify(
            {
                iconName: icon.iconName,
                prefix: icon.prefix,
                icon: icon.icon,
            },
            null,
            4,
        )};

`;
    });

    // Write the TypeScript file
    fs.writeFileSync(outputPath, content);
    console.log(`Generated Galaxy icons TypeScript exports at: ${outputPath}`);
    console.log(`Exported ${icons.length} icons: ${icons.map((i) => i.iconName).join(", ")}`);
}

// Run if called directly
if (require.main === module) {
    generateIconsTypeScript();
}

module.exports = generateIconsTypeScript;
