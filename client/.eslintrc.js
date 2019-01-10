module.exports = {
    extends: ["eslint:recommended", "prettier", "plugin:vue/essential"], // airbnb-base, eventually
    env: {
        browser: true
    },
    parserOptions: { parser: "babel-eslint" },
    plugins: ["prettier", "html"],
    rules: {
        //"no-console": "off",
        //"no-useless-escape": "off",
        //"no-debugger": "off",
        //"no-unused-vars": ["error", { args: "none" }],
        "prettier/prettier": [
            "error",
            {
                printWidth: 120,
                tabWidth: 4
            }
        ]
        // "camelcase": [
        //   "error",
        //   {
        //     "properties": "never"
        //   }
        // ]
    }
};
