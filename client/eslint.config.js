import js from "@eslint/js";

export default [
    js.configs.recommended,
    
    // Basic configuration for all files
    {
        files: ["**/*.js", "**/*.ts", "**/*.vue"],
        languageOptions: {
            ecmaVersion: 2020,
            sourceType: "module",
            globals: {
                window: "readonly",
                document: "readonly",
                console: "readonly",
                process: "readonly",
                Buffer: "readonly",
                global: "readonly",
                __dirname: "readonly",
                __filename: "readonly",
                module: "readonly",
                require: "readonly",
                exports: "readonly",
            },
        },
        rules: {
            // Standard rules
            "no-console": "off",
            "no-unused-vars": ["error", { args: "none", varsIgnorePattern: "_.+" }],
            "prefer-const": "error",
            "one-var": ["error", "never"],
            "curly": "error",
            "no-throw-literal": "error",
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
        ignores: ["dist/**", "src/libs/**", "src/nls/**", "src/legacy/**"],
    },
];