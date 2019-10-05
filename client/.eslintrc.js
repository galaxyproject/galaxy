module.exports = {
    extends: ["eslint:recommended", "plugin:vue/essential"], // airbnb-base, eventually
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
        "no-console": "off",
        "no-unused-vars": ["error", { args: "none" }],
        "prefer-const": "error",
        // I'd love to turn on camelcase, but it's a big shift with tons of current errors.
        // camelcase: [
        //     "error",
        //     {
        //         properties: "always"
        //     }
        // ]
    },
    globals: {
        // chai tests
        assert: true,
        expect: true
    }
};
