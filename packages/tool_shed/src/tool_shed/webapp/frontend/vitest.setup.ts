import { config } from "@vue/test-utils"
import { Quasar } from "quasar"
import { vSanitizeHtml } from "@galaxyproject/galaxy-ui"

// Quasar is still installed for the remaining q-selects
config.global.plugins = [[Quasar, {}]]
config.global.directives = { "sanitize-html": vSanitizeHtml }
