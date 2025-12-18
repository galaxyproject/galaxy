import { writeFileSync } from "fs";
import { resolve } from "path";
import { createHash } from "crypto";

/**
 * Vite plugin to generate build metadata JSON file
 */
export function buildMetadataPlugin(options = {}) {
    const { filename = resolve(__dirname, "../lib/galaxy/web/framework/meta.json"), buildDate = new Date() } = options;

    let buildHash = "";

    return {
        name: "vite-plugin-build-metadata",

        // Capture the build hash during bundle generation
        generateBundle(outputOptions, bundle) {
            // Get hash from the first JavaScript chunk
            for (const [fileName, chunk] of Object.entries(bundle)) {
                if (chunk.type === "chunk" && fileName.endsWith(".js")) {
                    // Extract hash from filename if present (e.g., chunk-[hash].js)
                    const hashMatch = fileName.match(/[.-]([a-f0-9]{8})[.-]/);
                    if (hashMatch) {
                        buildHash = hashMatch[1];
                        break;
                    }
                }
            }

            // If no hash found in filenames, generate one from bundle content
            if (!buildHash) {
                const bundleContent = Object.values(bundle)
                    .map((asset) => (asset.type === "chunk" ? asset.code : asset.source))
                    .join("");
                buildHash = createHash("md5").update(bundleContent).digest("hex").slice(0, 8);
            }
        },

        // Write the metadata file after build completes
        closeBundle() {
            const metadata = {
                hash: buildHash,
                epoch: Date.parse(buildDate),
            };

            try {
                writeFileSync(filename, JSON.stringify(metadata));
                console.log(`Build metadata written to ${filename}`);
            } catch (error) {
                console.error("Failed to write build metadata:", error);
                throw error;
            }
        },
    };
}
