module.exports = {
    root: true,
    parser: "vue-eslint-parser",
    parserOptions: {
        parser: "@typescript-eslint/parser",
        // project: ['./tsconfig.json'],
    },
    extends: [
        "plugin:vue/strongly-recommended",
        "eslint:recommended",
        "@vue/typescript/recommended",
        "prettier",
        "plugin:vuejs-accessibility/recommended",
        "plugin:@typescript-eslint/eslint-recommended",
        "plugin:@typescript-eslint/recommended",
        // More goodies..
        // "plugin:@typescript-eslint/recommended-requiring-type-checking",
    ],
    plugins: ["@typescript-eslint", "prettier", "vuejs-accessibility"],
    rules: {
        "prettier/prettier": "error",
        // not needed for vue 3
        "vue/no-multiple-template-root": "off",
        // upgrade warnings for common John problems
        "@typescript-eslint/no-unused-vars": "error",
        "vue/require-default-prop": "error",
        "vue/v-slot-style": "error",
    },
}
