import { describe, expect, it } from "vitest";

import { findForbiddenImports } from "../../scripts/check-style-imports.mjs";

function component(styleImport) {
    return `<template><div /></template>\n<style scoped lang="scss">\n${styleImport}\n</style>\n`;
}

describe("check-style-imports", () => {
    it.each([
        '@import "base";',
        '@import "base.scss";',
        '@import "@/style/scss/base.scss";',
        '@import "../../style/scss/base";',
        "@use 'base';",
        '@import"base";',
        '@import "theme/blue.scss", "base";',
        '@import "bootstrap";',
        '@import "bootstrap/scss/bootstrap";',
        '@import "bootstrap/scss/bootstrap.scss";',
        '@import "~bootstrap/scss/bootstrap";',
        '@import "../../../node_modules/bootstrap/scss/bootstrap";',
    ])("flags %s", (styleImport) => {
        expect(findForbiddenImports(component(styleImport))).toEqual([`3: ${styleImport}`]);
    });

    it.each([
        '@import "@/style/scss/theme/blue.scss";',
        '@import "bootstrap/scss/functions";',
        '@import "bootstrap/scss/_functions.scss";',
        '@import "bootstrap/scss/mixins";',
        '@import "bootstrap-vue/src/index.scss";',
        '@import "@/components/Form/_form-elements.scss";',
        '@import "x/database";',
        '// @import "base";',
    ])("allows %s", (styleImport) => {
        expect(findForbiddenImports(component(styleImport))).toEqual([]);
    });
});
