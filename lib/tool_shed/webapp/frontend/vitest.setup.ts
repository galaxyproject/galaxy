import { config } from "@vue/test-utils"
import { Quasar } from "quasar"

// Initialize Quasar for tests
config.global.plugins = [[Quasar, {}]]

// Configure global stubs for Quasar components if needed
// For now, we'll use real Quasar components but can stub if tests are slow
config.global.stubs = {}

