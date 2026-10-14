// Lint setup shared by every consumer of these components -- the client and the tool shed
// frontend -- for Vue 3 SFCs with TypeScript script blocks. Spread it last into `extends`
// so the parser pin wins over whatever the Vue plugin presets before it set.
import vuejsAccessibility from "eslint-plugin-vuejs-accessibility";
import tseslint from "typescript-eslint";
import vueParser from "vue-eslint-parser";

export const galaxyVueBase = [
    ...vuejsAccessibility.configs["flat/recommended"],
    {
        files: ["**/*.vue"],
        languageOptions: {
            // Plugin flat configs set the parser from their own dependency, so a stale nested
            // copy could win depending on order; pin the one the consumer installs.
            parser: vueParser,
            parserOptions: {
                // typescript-eslint rules need its parser services, even in components whose
                // script block is plain JS.
                parser: tseslint.parser,
                extraFileExtensions: [".vue"],
            },
        },
    },
];
