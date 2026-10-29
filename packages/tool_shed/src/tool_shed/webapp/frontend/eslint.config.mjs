import js from "@eslint/js"
import { galaxyVueBase } from "@galaxyproject/galaxy-ui/eslint"
import prettierRecommended from "eslint-plugin-prettier/recommended"
import vue from "eslint-plugin-vue"
import { defineConfig, globalIgnores } from "eslint/config"
import globals from "globals"
import tseslint from "typescript-eslint"

export default defineConfig(
    globalIgnores(["dist/**"]),
    {
        files: ["**/*.{ts,tsx,vue}"],
        extends: [
            js.configs.recommended,
            tseslint.configs.recommended,
            ...vue.configs["flat/strongly-recommended"],
            prettierRecommended,
            ...galaxyVueBase,
        ],
        languageOptions: {
            globals: globals.browser,
            parserOptions: {
                extraFileExtensions: [".vue"],
            },
        },
        rules: {
            // upgrade warnings for common John problems
            "@typescript-eslint/no-unused-vars": "error",
            "vue/require-default-prop": "error",
            "vue/v-slot-style": "error",
            // Markup goes through v-sanitize-html (DOMPurify) instead.
            "vue/no-v-html": "error",
            // In typescript-eslint's recommended set before v8; kept so these still show up.
            "@typescript-eslint/adjacent-overload-signatures": "error",
            "@typescript-eslint/no-empty-function": "error",
            "@typescript-eslint/no-inferrable-types": "error",
            "@typescript-eslint/no-non-null-assertion": "warn",
        },
    },
    // typescript-eslint scopes these overrides (no-var, prefer-const, ...) to .ts files; the
    // old @vue/eslint-config-typescript applied them to components too.
    { ...tseslint.configs.eslintRecommended, files: ["**/*.vue"] },
)
