#!/usr/bin/env node
// Components must not import stylesheets that emit CSS. In a <style scoped> block every
// selector gets the component's [data-v-*] attribute, so each import compiles a fresh,
// un-dedupable copy of Bootstrap and friends into base.css (see #23703).
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

const ROOTS = ["src", "packages/ui/src"];
const FORBIDDEN = [/["'](@\/style\/scss\/)?base(\.scss)?["']/, /["']bootstrap\/scss\/bootstrap(\.scss)?["']/];
const IMPORT = /^\s*@(import|use)\s+(.+)$/;

const problems = [];
for (const root of ROOTS) {
    for (const entry of readdirSync(root, { recursive: true, withFileTypes: true })) {
        if (!entry.isFile() || !entry.name.endsWith(".vue")) {
            continue;
        }
        const path = join(entry.parentPath, entry.name);
        readFileSync(path, "utf8")
            .split("\n")
            .forEach((line, index) => {
                const match = line.match(IMPORT);
                if (match && FORBIDDEN.some((pattern) => pattern.test(match[2]))) {
                    problems.push(`${relative(".", path)}:${index + 1}: ${line.trim()}`);
                }
            });
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
