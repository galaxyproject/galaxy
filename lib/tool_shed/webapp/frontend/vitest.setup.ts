import { config } from "@vue/test-utils"
import { Quasar } from "quasar"

// Quasar is still installed for the remaining q-selects
config.global.plugins = [[Quasar, {}]]

// main.ts registers a no-op g-tooltip, since GTable reaches for the client's directive
config.global.directives = { "g-tooltip": {} }
