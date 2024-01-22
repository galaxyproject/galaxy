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
import router from "@/router"
import { createPinia } from "pinia"
import { apolloClientProvider, apolloClient } from "@/apollo"
import { DefaultApolloClient } from "@vue/apollo-composable"

createApp(App)
    .provide(DefaultApolloClient, apolloClient)
    .use(apolloClientProvider)
    .use(createPinia())
    .use(router)
    .use(Quasar, { plugins: { Notify, Cookies } })
    .mount("#app")
