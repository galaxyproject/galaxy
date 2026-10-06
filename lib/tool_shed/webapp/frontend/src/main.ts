import { createApp } from "vue"
import { Quasar } from "quasar"
import App from "./App.vue"
// Quasar's own chrome (select arrows, table pagination and sort) draws SVG FontAwesome
// icons from this set, so no icon webfont ships with the app
import iconSet from "quasar/icon-set/svg-fontawesome-v6"
import "quasar/src/css/index.sass"

// Galaxy brand: cross-property design tokens (--color-galaxy-*) and the
// Atkinson Hyperlegible face used across Galaxy web properties.
import "@galaxyproject/brand-tokens/tokens.css"
// galaxy-ui component token contract (--color-*/--spacing-* custom properties)
import "@galaxyproject/galaxy-ui/tokens.css"
import "@fontsource/atkinson-hyperlegible/400.css"
import "@fontsource/atkinson-hyperlegible/400-italic.css"
import "@fontsource/atkinson-hyperlegible/700.css"
import "@fontsource/atkinson-hyperlegible/700-italic.css"
import "@/styles/shed.css"
import router from "@/router"
import { createPinia } from "pinia"

// Quasar now only provides q-select and the markup inside it (RevisionSelect, SelectUser, OverviewTab)
const quasarConfig = { iconSet }
const app = createApp(App).use(createPinia()).use(router).use(Quasar, quasarConfig)
// galaxy-ui's GTable decorates a few controls with the Galaxy client's v-g-tooltip; here they keep
// their native title, and registering a no-op stops Vue warning about the directive on every render
app.directive("g-tooltip", {})
app.mount("#app")
