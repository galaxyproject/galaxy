module.exports = {
    extends: ["eslint:recommended", "plugin:vue/essential"], // airbnb-base, eventually
    env: {
        browser: true
    },
    parserOptions: { parser: "babel-eslint" },
    plugins: ["html"],
    rules: {
        "no-console": "off",
        "no-unused-vars": ["error", { args: "none" }],
        // I'd love to turn on camelcase, but it's a big shift with tons of current errors.
        // camelcase: [
        //     "error",
        //     {
        //         properties: "always"
        //     }
        // ]
    }
};
