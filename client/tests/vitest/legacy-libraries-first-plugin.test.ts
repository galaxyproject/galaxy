import { createRequire } from "node:module";
import { dirname, join } from "node:path";

import { describe, expect, it } from "vitest";

import { legacyLibrariesFirstPlugin } from "../../vite-plugin-legacy-libraries-first.js";

const MARKER_IMPORT = 'import "@/legacy-libraries.js";\n';

function transform(id: string) {
    return legacyLibrariesFirstPlugin().transform("export default 1;", id);
}

describe("legacyLibrariesFirstPlugin", () => {
    it("prepends the marker import to bootstrap-vue's installed vue.js", () => {
        // The real resolved path, so a pnpm layout or bootstrap-vue change that
        // moves the module fails here instead of silently skipping the import.
        const packageJson = createRequire(import.meta.url).resolve("bootstrap-vue/package.json");
        const id = join(dirname(packageJson), "esm", "vue.js");
        expect(transform(id)?.code.startsWith(MARKER_IMPORT)).toBe(true);
    });

    it("matches Windows paths", () => {
        const id = "C:\\galaxy\\client\\node_modules\\bootstrap-vue\\esm\\vue.js";
        expect(transform(id)?.code.startsWith(MARKER_IMPORT)).toBe(true);
    });

    it("leaves other modules alone", () => {
        expect(transform("/galaxy/client/node_modules/bootstrap-vue/esm/index.js")).toBeUndefined();
        expect(transform("/galaxy/client/src/legacy-libraries.js")).toBeUndefined();
    });
});
