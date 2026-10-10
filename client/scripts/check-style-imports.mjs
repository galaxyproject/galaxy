#!/usr/bin/env node
// Components must not import stylesheets that emit CSS. In a <style scoped> block every
// selector gets the component's [data-v-*] attribute, so each import compiles a fresh,
// un-dedupable copy of Bootstrap and friends into base.css (see #23703).
import { readdirSync, readFileSync, realpathSync } from "node:fs";
import { join, relative } from "node:path";

const ROOTS = ["src", "packages/ui/src"];
// A bare "bootstrap" also pulls in everything: it resolves through the package's "sass" field.
const FORBIDDEN = [/["'](?:[^"']*\/)?base(?:\.scss)?["']/, /["'](?:[^"']*\/)?~?bootstrap(?:\.scss)?["']/];
const IMPORT = /^\s*@(?:import|use)\b(.+)$/;

export function findForbiddenImports(source) {
    return source.split("\n").flatMap((line, index) => {
        const match = line.match(IMPORT);
        return match && FORBIDDEN.some((pattern) => pattern.test(match[1])) ? [`${index + 1}: ${line.trim()}`] : [];
    });
}

function main() {
    const client = join(import.meta.dirname, "..");
    const problems = [];
    for (const root of ROOTS) {
        for (const entry of readdirSync(join(client, root), { recursive: true, withFileTypes: true })) {
            if (!entry.isFile() || !entry.name.endsWith(".vue")) {
                continue;
            }
            const path = join(entry.parentPath, entry.name);
            for (const problem of findForbiddenImports(readFileSync(path, "utf8"))) {
                problems.push(`${relative(".", path)}:${problem}`);
            }
        }
    }

    if (problems.length) {
        console.error("Components must not import base.scss or all of Bootstrap:\n");
        console.error(problems.map((problem) => `  ${problem}`).join("\n"));
        console.error(
            '\nEach import adds a full scoped copy (~600 KB) to base.css. Import "@/style/scss/theme/blue.scss"' +
                "\nfor variables instead.",
        );
        process.exit(1);
    }
}

if (process.argv[1] && realpathSync(process.argv[1]) === import.meta.filename) {
    main();
}
