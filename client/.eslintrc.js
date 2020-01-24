module.exports = {
    extends: [
        "eslint:recommended",
        //"plugin:vue/strongly-recommended",
        "plugin:vue/essential",
        //"airbnb-base", eventually
    ],
    env: {
        browser: true,
        commonjs: true,
        es6: true,
        node: true,
        mocha: true
    },
    parserOptions: {
        parser: "babel-eslint",
        sourceType: "module"
    },
    plugins: ["html"],
    rules: {
        // Standard rules
        "no-console": "off",
        "no-unused-vars": ["error", { args: "none" }],
        "prefer-const": "error",
        "vue/v-on-style": "error",
        "vue/v-bind-style": "error",
        "vue/attribute-hyphenation": "error",

        // Vue.  Prettier compat workarounds, mostly.
        "vue/html-indent": "off",
        "vue/max-attributes-per-line": "off",
        "vue/singleline-html-element-content-newline": "off",
        "vue/multiline-html-element-content-newline": "off",
        "vue/html-closing-bracket-newline": "off"
    },
    globals: {
        // chai tests
        assert: true,
        expect: true
    }
};
