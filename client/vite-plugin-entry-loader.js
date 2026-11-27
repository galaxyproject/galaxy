// Emits a stable <entry>.bundled.js loader per entry, so the ?v= script tag and lazy chunks share one module URL.
export function entryLoaderPlugin() {
    return {
        name: "vite-plugin-galaxy-entry-loader",
        apply: "build",

        generateBundle(_outputOptions, bundle) {
            const entries = Object.values(bundle).filter((chunk) => chunk.type === "chunk" && chunk.isEntry);
            for (const chunk of entries) {
                this.emitFile({
                    type: "asset",
                    fileName: `${chunk.name}.bundled.js`,
                    source: `import "./${chunk.fileName}";\n`,
                });
            }
        },
    };
}
