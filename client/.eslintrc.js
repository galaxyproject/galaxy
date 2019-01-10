module.exports = {
    extends: ["eslint:recommended", "plugin:vue/essential"], // airbnb-base, eventually
    env: {
        browser: true
    },
    parserOptions: { parser: "babel-eslint" },
    plugins: ["html"],
    rules: {
        "no-console": "off",
        "no-unused-vars": ["error", {args: "none"}]
        // "camelcase": [
        //   "error",
        //   {
        //     "properties": "never"
        //   }
        // ]
    }
};
