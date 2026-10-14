import { defineConfig } from "vitest/config"
import { fileURLToPath } from "url"
import vue from "@vitejs/plugin-vue"
import { quasar, transformAssetUrls } from "@quasar/vite-plugin"

export default defineConfig({
    plugins: [
        vue({
            template: { transformAssetUrls },
        }),
        quasar({
            sassVariables: "src/quasar-variables.sass",
        }),
    ],
    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: ["./vitest.setup.ts"],
        server: {
            deps: {
                // raw-source package: force vitest to transform the SFCs
                inline: ["@galaxyproject/galaxy-ui"],
            },
        },
    },
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
})
