import { fileURLToPath } from "url"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import { quasar, transformAssetUrls } from "@quasar/vite-plugin"

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        vue({
            template: { transformAssetUrls },
        }),

        quasar({
            sassVariables: "src/quasar-variables.sass",
        }),
    ],
    build: {},
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
    server: {
        proxy: {
            "/api": {
                target: process.env.TOOL_SHED_URL || "http://127.0.0.1:9009",
                changeOrigin: process.env.CHANGE_ORIGIN ? !process.env.CHANGE_ORIGIN : true,
                secure: !process.env.CHANGE_ORIGIN,
            },
        },
    },
})
