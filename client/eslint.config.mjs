import js from "@eslint/js";
import compat from "eslint-plugin-compat";
import importPlugin from "eslint-plugin-import";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import vue from "eslint-plugin-vue";
import vueAccessibility from "eslint-plugin-vuejs-accessibility";
import tseslint from "typescript-eslint";
import vueParser from "vue-eslint-parser";
import globals from "globals";

const baseRules = {
    // Standard rules
    "no-console": "off",
    "no-unused-vars": ["error", { args: "none", varsIgnorePattern: "_.+" }],
    "prefer-const": "error",
    "one-var": ["error", "never"],
    curly: "error",
    "no-throw-literal": "error",

    "vue/valid-v-slot": "error",
    "vue/v-slot-style": ["error", { atComponent: "v-slot", default: "v-slot", named: "longform" }],

    // Vue 3 specific rules
    "vue/no-deprecated-dollar-listeners-api": "error",
    "vue/no-deprecated-dollar-scopedslots-api": "error",
    "vue/no-deprecated-events-api": "error",
    "vue/no-deprecated-filter": "error",
    "vue/no-deprecated-functional-template": "error",
    "vue/no-deprecated-inline-template": "error",
    "vue/no-deprecated-props-default-this": "error",
    "vue/no-deprecated-router-link-tag-prop": "error",
    "vue/no-deprecated-scope-attribute": "error",
    "vue/no-deprecated-slot-attribute": "error",
    "vue/no-deprecated-slot-scope-attribute": "error",
    "vue/no-deprecated-v-bind-sync": "error",
    "vue/no-deprecated-v-on-number-modifiers": "error",
    "vue/no-deprecated-vue-config-keycodes": "error",
    "vue/no-lifecycle-after-await": "error",
    "vue/no-ref-as-operand": "error",
    "vue/no-v-for-template-key-on-child": "error",
    "vue/require-explicit-emits": "warn",

    // Downgrade the severity of some rules to warnings as a transition measure.
    "vue/multi-word-component-names": "warn",
    "vue/component-name-in-template-casing": "error",
    "vue/prop-name-casing": "warn",
    "vue/require-prop-types": "warn",
    "vue/require-default-prop": "warn",
    "vue/no-v-html": "warn",

    // Increase the severity of some rules to errors
    "vue/attributes-order": "error",
    "vue/order-in-components": "error",

    // Prettier compromises/workarounds -- mostly #wontfix?
    "vue/html-indent": "off",
    "vue/max-attributes-per-line": "off",
    "vue/html-self-closing": "off",
    "vue/singleline-html-element-content-newline": "off",
    "vue/multiline-html-element-content-newline": "off",
    "vue/html-closing-bracket-newline": "off",
    "vue/html-closing-bracket-spacing": "off",

    // Accessibility rules
    "vuejs-accessibility/alt-text": "error",
    "vuejs-accessibility/anchor-has-content": "warn",
    "vuejs-accessibility/click-events-have-key-events": "warn",
    "vuejs-accessibility/form-control-has-label": "warn",
    "vuejs-accessibility/heading-has-content": "error",
    "vuejs-accessibility/iframe-has-title": "error",
    "vuejs-accessibility/label-has-for": [
        "warn",
        {
            required: {
                some: ["nesting", "id"],
            },
            allowChildren: true,
        },
    ],
    "vuejs-accessibility/mouse-events-have-key-events": "warn",
    "vuejs-accessibility/no-autofocus": "error",
    "vuejs-accessibility/no-static-element-interactions": "warn",
    "vuejs-accessibility/tabindex-no-positive": "error",

    // import and export sorting and linting.
    "simple-import-sort/imports": [
        "error",
        {
            groups: [
                // Side effect imports.
                ["^\\u0000"],
                // Node.js builtins prefixed with `node:`.
                ["^node:"],
                // Packages.
                // Things that start with a letter (or digit or underscore), or `@` followed by a letter.
                ["^@?\\w"],
                // Absolute imports and other imports such as Vue-style `@/foo`.
                // Anything not matched in another group.
                ["^"],
                // Relative imports.
                // Anything that starts with a dot.
                ["^\\."],
                // anything that ends in .vue
                ["\\.vue$"],
            ],
        },
    ],
    "simple-import-sort/exports": "error",
    "import/first": "error",
    "import/newline-after-import": "error",
    "import/no-duplicates": "error",
};

export default [
    // Base configuration for JavaScript and Vue files
    {
        files: ["**/*.js", "**/*.vue"],
        languageOptions: {
            ecmaVersion: 2020,
            sourceType: "module",
            globals: {
                ...globals.browser,
                ...globals.node,
            },
        },
        plugins: {
            vue,
            compat,
            "simple-import-sort": simpleImportSort,
            import: importPlugin,
            "vuejs-accessibility": vueAccessibility,
        },
        rules: {
            ...js.configs.recommended.rules,
            ...baseRules,
        },
    },

    // Vue files specific configuration
    {
        files: ["**/*.vue"],
        languageOptions: {
            parser: vueParser,
            parserOptions: {
                parser: "espree",
                ecmaVersion: 2020,
                sourceType: "module",
            },
        },
    },

    // TypeScript files configuration
    ...tseslint.configs.recommended.map((config) => ({
        ...config,
        files: ["**/*.ts", "**/*.tsx"],
    })),
    {
        files: ["**/*.ts", "**/*.tsx"],
        languageOptions: {
            parser: tseslint.parser,
            parserOptions: {
                ecmaFeatures: { jsx: true },
                ecmaVersion: 2020,
                sourceType: "module",
                project: true,
            },
        },
        plugins: {
            "@typescript-eslint": tseslint.plugin,
            vue,
            compat,
            "simple-import-sort": simpleImportSort,
            import: importPlugin,
            "vuejs-accessibility": vueAccessibility,
        },
        rules: {
            ...baseRules,
            "@typescript-eslint/ban-ts-comment": "warn",
            "@typescript-eslint/no-explicit-any": "warn",
            "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "_.+", varsIgnorePattern: "_.+" }],
        },
    },

    // Vue files with TypeScript
    {
        files: ["**/*.vue"],
        languageOptions: {
            parser: vueParser,
            parserOptions: {
                parser: tseslint.parser,
                extraFileExtensions: [".vue"],
                ecmaVersion: 2020,
                sourceType: "module",
            },
        },
    },

    // Test files configuration
    {
        files: ["**/*.test.js", "**/*.test.ts", "**/tests/jest/**"],
        languageOptions: {
            globals: {
                jest: "readonly",
                describe: "readonly",
                it: "readonly",
                test: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterEach: "readonly",
                beforeAll: "readonly",
                afterAll: "readonly",
            },
        },
    },

    // Ignore patterns
    {
        ignores: [
            "**/dist/**",
            "src/libs/**",
            "src/nls/**",
            "src/legacy/**",
            "**/node_modules/**",
            "build/**",
            "*.min.js",
        ],
    },
];
