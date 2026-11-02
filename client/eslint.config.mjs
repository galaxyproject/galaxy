import js from "@eslint/js";
import { galaxyVueBase } from "@galaxyproject/galaxy-ui/eslint";
import { defineConfig, globalIgnores } from "eslint/config";
import compat from "eslint-plugin-compat";
import importX from "eslint-plugin-import-x";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import vue from "eslint-plugin-vue";
import globals from "globals";
import tseslint from "typescript-eslint";

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
    "vue/no-deprecated-delete-set": "error",
    "vue/no-deprecated-events-api": "error",
    // The vue/no-deprecated-* rules only see components in .vue files, so the
    // render-function providers in .js files need a plain property check.
    "no-restricted-properties": [
        "error",
        ...["$scopedSlots", "$children", "$set", "$delete", "$destroy"].map((property) => ({
            property,
            message: `${property} is Vue 2 instance API; compat has it turned off for Galaxy code.`,
        })),
    ],
    // RENDER_FUNCTION is off, so a render function's first argument is the
    // instance proxy, not `h`.
    "no-restricted-syntax": [
        "error",
        {
            selector:
                "Property[key.name='render'] > :matches(FunctionExpression, ArrowFunctionExpression)[params.0.name=/^(h|createElement)$/]",
            message: "Vue 3 render functions don't receive `h`; import { h } from 'vue' instead.",
        },
    ],
    "vue/no-deprecated-data-object-declaration": "error",
    "vue/no-deprecated-destroyed-lifecycle": "error",
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
    "vue/no-deprecated-v-on-native-modifier": "error",
    "vue/no-deprecated-html-element-is": "error",
    "vue/no-use-v-if-with-v-for": "error",
    // A bare <template> renders as a native <template> element under Vue 3.
    "vue/no-lone-template": "error",
    "vue/no-lifecycle-after-await": "error",
    "vue/no-ref-as-operand": "error",
    "vue/no-v-for-template-key-on-child": "error",
    // Undeclared emits fall through to the root element as native listeners
    // once INSTANCE_LISTENERS is off.
    "vue/require-explicit-emits": "error",
    // Bootstrap-vue isn't registered globally, so its components have to be
    // imported where they're used. Only checks bootstrap-vue names.
    "vue/no-undef-components": ["error", { ignorePatterns: ["^(?!b-|B[A-Z])"] }],
    // One entry for every restricted import: a second "no-restricted-imports"
    // key in this object would silently replace the first.
    "no-restricted-imports": [
        "error",
        {
            paths: [
                // client/patches/bootstrap-vue@2.23.1.patch doesn't fix v-model on these under
                // Vue 3 compat, so they'd silently stop updating their bound values.
                {
                    name: "bootstrap-vue",
                    importNames: [
                        "BFormCheckbox",
                        "BFormCheckboxGroup",
                        "BFormRadio",
                        "BFormRadioGroup",
                        "BFormSelect",
                        "BFormTags",
                    ],
                    message:
                        "Unpatched under Vue 3 compat; use GCheckbox, GCheckboxGroup, GRadio, GRadioGroup or GSelect.",
                },
                // Vue 2 libraries have to be marked with legacyComponent() to keep their
                // compat behavior, so each has one marked import path.
                {
                    name: "vue-json-pretty",
                    message: "Import @/components/Common/legacy/VueJsonPretty, which keeps it on compat MODE 2.",
                },
                {
                    name: "@handsontable/vue",
                    message: "Import @/components/Common/legacy/HotTable, which keeps it on compat MODE 2.",
                },
            ],
        },
    ],

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
    "import-x/first": "error",
    "import-x/newline-after-import": "error",
    "import-x/no-duplicates": "error",
};

const typeImportRules = {
    "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports", fixStyle: "inline-type-imports" },
    ],
    "@typescript-eslint/no-import-type-side-effects": "error",
};

export default defineConfig(
    globalIgnores(["dist/**", "src/libs/**", "src/nls/**", "src/legacy/**", "packages/api-client/**"]),
    {
        files: ["**/*.{js,mjs,cjs,ts,tsx,vue}"],
        extends: [
            js.configs.recommended,
            compat.configs["flat/recommended"],
            ...vue.configs["flat/recommended"],
            ...galaxyVueBase,
        ],
        plugins: {
            "@typescript-eslint": tseslint.plugin,
            "import-x": importX,
            "simple-import-sort": simpleImportSort,
        },
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node,
            },
        },
        rules: baseRules,
    },
    {
        files: ["src/components/Common/legacy/**"],
        rules: { "no-restricted-imports": "off" },
    },
    {
        // Still waiting on Phase 3, which rewrites the Form/Elements emits.
        // Drop each entry as it lands.
        files: ["src/components/Form/Elements/FormNumber.vue", "src/components/Form/Elements/FormText.vue"],
        rules: {
            "vue/require-explicit-emits": "warn",
        },
    },
    {
        files: ["**/*.test.js", "**/*.test.ts", "**/tests/vitest/**"],
        languageOptions: {
            globals: globals.vitest,
        },
    },
    {
        files: ["**/*.ts", "**/*.tsx", "**/*.vue"],
        rules: typeImportRules,
    },
    {
        files: ["**/*.ts", "**/*.tsx"],
        extends: [
            tseslint.configs.recommended,
            // tseslint.configs.stylistic,  // TODO: work towards this
        ],
        languageOptions: {
            parserOptions: {
                ecmaFeatures: { jsx: true },
                extraFileExtensions: [".vue"],
                projectService: true,
            },
        },
        rules: {
            // The base rule can't see TS types; typescript-eslint's replacements handle these.
            "no-throw-literal": "off",
            "no-unused-vars": "off",
            "@typescript-eslint/only-throw-error": "error",
            "@typescript-eslint/ban-ts-comment": "warn",
            "@typescript-eslint/no-explicit-any": "warn", // TODO: re-enable this
            "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "_.+", varsIgnorePattern: "_.+" }],
        },
    },
);
