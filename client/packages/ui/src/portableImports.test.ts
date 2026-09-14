import { readdirSync, readFileSync, statSync } from "fs";
import { join } from "path";
import { describe, expect, it } from "vitest";

/**
 * The package ships raw source and declares peer ranges spanning two major
 * versions of Vue and vue-router, so every consumer compiles these files with
 * its own stack: the Galaxy client on Vue 2.7 / vue-router 3, external
 * consumers (the Tool Shed frontend) on Vue 3 / vue-router 4.
 *
 * An import that only resolves on one of them type-checks and builds fine for
 * whoever added it and breaks the other consumer at compile time, which is how
 * `vue-router/composables` -- a 3.x-only entry point -- reached the package.
 * Reach cross-version APIs through something both versions install instead
 * (see GToast's use of `$router` off the component instance).
 */
const VERSION_LOCKED_SPECIFIERS = [
    // vue-router 3 only; on 4.x the composables live at the package root.
    "vue-router/composables",
    // Vue 2 only; Vue 3 has the composition API built in.
    "@vue/composition-api",
    // Build-specific Vue entry points differ between the two majors.
    "vue/dist/vue.esm-bundler",
    "vue/dist/vue.esm.js",
    "vue/dist/vue.runtime.esm-bundler",
];

const SOURCE_EXTENSIONS = [".ts", ".js", ".vue"];

function sourceFiles(directory: string): string[] {
    return readdirSync(directory).flatMap((entry) => {
        const path = join(directory, entry);
        if (statSync(path).isDirectory()) {
            return sourceFiles(path);
        }
        if (path.endsWith(".test.ts") || path.endsWith(".test.js")) {
            // Skip tests -- this file names the banned specifiers as data.
            return [];
        }
        return SOURCE_EXTENSIONS.some((extension) => path.endsWith(extension)) ? [path] : [];
    });
}

describe("galaxy-ui source portability", () => {
    const packageSource = join(__dirname);
    const files = sourceFiles(packageSource);

    it("finds the package sources to check", () => {
        // An empty list would make every assertion below vacuously true.
        expect(files.length).toBeGreaterThan(10);
    });

    it.each(VERSION_LOCKED_SPECIFIERS)("imports nothing from %s", (specifier) => {
        // Match the specifier only where it is actually resolved, so that prose
        // naming it -- like GToast's comment explaining why it is avoided --
        // does not read as a violation.
        const escaped = specifier.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const importPattern = new RegExp(`(?:from|import|require)\\s*\\(?\\s*["']${escaped}["']`);
        const offenders = files.filter((file) => importPattern.test(readFileSync(file, "utf-8")));
        expect(
            offenders.map((file) => file.slice(packageSource.length + 1)),
            `${specifier} resolves for only one of the supported peer versions`,
        ).toEqual([]);
    });
});
