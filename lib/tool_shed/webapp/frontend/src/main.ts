import { createApp } from "vue"
import { Quasar, Notify, Cookies } from "quasar"
import App from "./App.vue"
// <q-icon icon="<icon_name>"
import "@quasar/extras/material-icons/material-icons.css"
// <q-icon icon="sym_r_<icon_name>"
import "@quasar/extras/material-symbols-rounded/material-symbols-rounded.css"

// Not needed...
// import "@quasar/extras/material-icons-outlined/material-icons-outlined.css"
// import "@quasar/extras/material-symbols-outlined/material-symbols-outlined.css"
import "quasar/src/css/index.sass"
// galaxy-ui component token contract (--color-*/--spacing-* custom properties)
import "@galaxyproject/galaxy-ui/tokens.css"
import router from "@/router"
import { createPinia } from "pinia"

const quasarPlugins = { Notify, Cookies }
const quasarConfig = { plugins: quasarPlugins }
createApp(App).use(createPinia()).use(router).use(Quasar, quasarConfig).mount("#app")
