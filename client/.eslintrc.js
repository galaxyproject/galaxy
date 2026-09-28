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
    // For example, vue/multi-word-component names is considered an error,
    // but that kind of refactoring is best done slowly, one bit at a time
    // as those components are touched.
    "vue/multi-word-component-names": "warn",
    "vue/component-name-in-template-casing": "error",
    "vue/prop-name-casing": "warn",
    "vue/require-prop-types": "warn",
    "vue/require-default-prop": "warn",

    // Increase the severity of some rules to errors
    "vue/attributes-order": "error",
    "vue/order-in-components": "error",
    // Markup goes through v-sanitize-html (DOMPurify); v-no-sanitize-html is the
    // reviewed exception for server/shipped markup, with a comment saying why.
    "vue/no-v-html": "error",
    // v-no-sanitize-html skips DOMPurify, so each use has to disable this rule
    // inline with a reason after "--".
    "vue/no-restricted-syntax": [
        "error",
        {
            selector: "VAttribute[directive=true][key.name.name='no-sanitize-html']",
            message:
                "v-no-sanitize-html skips DOMPurify. Prefer v-sanitize-html; if the markup really is trusted, disable this line with a reason.",
        },
    ],

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

    "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports", fixStyle: "inline-type-imports" },
    ],

    "@typescript-eslint/no-import-type-side-effects": "error",
};

const baseExtends = [
    "eslint:recommended",
    "plugin:compat/recommended",
    "plugin:vue/vue3-recommended",
    "plugin:vuejs-accessibility/recommended",
];

const basePlugins = ["simple-import-sort", "import"];

module.exports = {
    root: true,
    extends: baseExtends,
    env: {
        browser: true,
        node: true,
        es6: true,
    },
    rules: baseRules,
    ignorePatterns: ["dist", "src/libs", "src/nls", "src/legacy", "packages/api-client"],
    plugins: basePlugins,
    overrides: [
        {
            files: ["**/*.test.js", "**/*.test.ts", "**/tests/vitest/**"],
            globals: {
                vi: "readonly",
                describe: "readonly",
                it: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterEach: "readonly",
                beforeAll: "readonly",
                afterAll: "readonly",
                test: "readonly",
            },
        },
        {
            files: ["**/*.vue"],
            parser: "vue-eslint-parser",
            parserOptions: {
                parser: {
                    js: "espree",
                    ts: "@typescript-eslint/parser",
                },
            },
        },
        {
            files: ["**/*.ts", "**/*.tsx"],
            extends: [
                ...baseExtends,
                "plugin:@typescript-eslint/recommended",
                // "plugin:@typescript-eslint/stylistic"  // TODO: work towards this
            ],
            rules: {
                ...baseRules,
                "@typescript-eslint/no-throw-literal": "error",
                "@typescript-eslint/ban-ts-comment": "warn",
                "@typescript-eslint/no-explicit-any": "warn", // TODO: re-enable this
                "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "_.+", varsIgnorePattern: "_.+" }],
            },
            parser: "@typescript-eslint/parser",
            parserOptions: {
                ecmaFeatures: { jsx: true },
                ecmaVersion: 2020,
                sourceType: "module",
                extraFileExtensions: [".vue"],
                project: true,
            },
            plugins: [...basePlugins, "@typescript-eslint"],
        },
        {
            // galaxy-ui supports Vue 2.7 and 3 at once (the tool shed consumes it too), so its
            // components keep `.native` for vue-router 3's RouterLink roots.
            files: ["packages/ui/src/**/*.vue"],
            rules: {
                "vue/no-deprecated-v-on-native-modifier": "off",
            },
        },
    ],
};
