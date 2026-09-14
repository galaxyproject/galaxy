import { createApp } from "vue"
import { Quasar, Cookies } from "quasar"
import App from "./App.vue"
// <q-icon icon="<icon_name>"
import "@quasar/extras/material-icons/material-icons.css"
// <q-icon icon="sym_r_<icon_name>"
import "@quasar/extras/material-symbols-rounded/material-symbols-rounded.css"

// Not needed...
// import "@quasar/extras/material-icons-outlined/material-icons-outlined.css"
// import "@quasar/extras/material-symbols-outlined/material-symbols-outlined.css"
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
import router from "@/router"
import { createPinia } from "pinia"

const quasarPlugins = { Cookies }
const quasarConfig = { plugins: quasarPlugins }
createApp(App).use(createPinia()).use(router).use(Quasar, quasarConfig).mount("#app")
