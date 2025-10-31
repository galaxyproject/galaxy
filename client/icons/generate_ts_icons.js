const fs = require("fs");
const path = require("path");

/**
 * Generate TypeScript exports for Galaxy custom icons
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

// Galaxy custom icons
// Generated from: ${iconsJsonPath}
// To regenerate, run: npm run icons

// Matches FontAwesome's structure
export interface GalaxyIconDefinition {
    iconName: string;
    prefix: string;
    icon: [number, number, never[], string, string | string[]];
}

// Accepts both FA and Galaxy icons
export type IconLike = IconDefinition | GalaxyIconDefinition;

`;

    icons.forEach((icon) => {
        // Convert icon name to camelCase for JavaScript export
        const exportName = icon.iconName;

        content += `export const ${exportName}: GalaxyIconDefinition = ${JSON.stringify(
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
