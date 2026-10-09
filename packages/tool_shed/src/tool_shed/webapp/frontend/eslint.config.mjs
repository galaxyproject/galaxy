import js from "@eslint/js"
import prettierRecommended from "eslint-plugin-prettier/recommended"
import vue from "eslint-plugin-vue"
import vuejsAccessibility from "eslint-plugin-vuejs-accessibility"
import { defineConfig, globalIgnores } from "eslint/config"
import globals from "globals"
import tseslint from "typescript-eslint"
import vueParser from "vue-eslint-parser"

export default defineConfig(
    globalIgnores(["dist/**"]),
    {
        files: ["**/*.{ts,tsx,vue}"],
        extends: [
            js.configs.recommended,
            tseslint.configs.recommended,
            ...vue.configs["flat/strongly-recommended"],
            prettierRecommended,
            ...vuejsAccessibility.configs["flat/recommended"],
        ],
        languageOptions: {
            globals: globals.browser,
            parserOptions: {
                parser: tseslint.parser,
                extraFileExtensions: [".vue"],
            },
        },
        rules: {
            // upgrade warnings for common John problems
            "@typescript-eslint/no-unused-vars": "error",
            "vue/require-default-prop": "error",
            "vue/v-slot-style": "error",
            // In typescript-eslint's recommended set before v8; kept so these still show up.
            "@typescript-eslint/adjacent-overload-signatures": "error",
            "@typescript-eslint/no-empty-function": "error",
            "@typescript-eslint/no-inferrable-types": "error",
            "@typescript-eslint/no-non-null-assertion": "warn",
        },
    },
    {
        // Plugin flat configs set the parser from their own dependency, so a stale nested copy
        // could win depending on order; pin the one we install.
        files: ["**/*.vue"],
        languageOptions: {
            parser: vueParser,
        },
    },
    // typescript-eslint scopes these overrides (no-var, prefer-const, ...) to .ts files; the
    // old @vue/eslint-config-typescript applied them to components too.
    { ...tseslint.configs.eslintRecommended, files: ["**/*.vue"] },
)
