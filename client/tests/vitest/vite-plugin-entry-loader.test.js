import { describe, expect, it } from "vitest";

import { entryLoaderPlugin } from "../../vite-plugin-entry-loader.js";

function runGenerateBundle(bundle) {
    const emitted = [];
    entryLoaderPlugin().generateBundle.call({ emitFile: (file) => emitted.push(file) }, {}, bundle);
    return emitted;
}

describe("entryLoaderPlugin", () => {
    it("emits a stable-name loader for each entry chunk that imports its hashed file", () => {
        const emitted = runGenerateBundle({
            "analysis-AbC123.js": { type: "chunk", isEntry: true, name: "analysis", fileName: "analysis-AbC123.js" },
            "libs-Def456.js": { type: "chunk", isEntry: true, name: "libs", fileName: "libs-Def456.js" },
        });
        expect(emitted).toEqual([
            { type: "asset", fileName: "analysis.bundled.js", source: 'import "./analysis-AbC123.js";\n' },
            { type: "asset", fileName: "libs.bundled.js", source: 'import "./libs-Def456.js";\n' },
        ]);
    });

    it("skips lazy chunks and assets", () => {
        const emitted = runGenerateBundle({
            "CustomToolEditor-x1.js": {
                type: "chunk",
                isEntry: false,
                isDynamicEntry: true,
                name: "CustomToolEditor",
                fileName: "CustomToolEditor-x1.js",
            },
            "base.css": { type: "asset", fileName: "base.css" },
        });
        expect(emitted).toEqual([]);
    });
});
