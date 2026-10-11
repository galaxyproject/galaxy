import { config } from "@vue/test-utils"
import { Quasar } from "quasar"

// Quasar is still installed for the remaining q-selects
config.global.plugins = [[Quasar, {}]]
