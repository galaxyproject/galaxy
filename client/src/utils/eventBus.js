import mitt from "mitt";

// Create a global event bus for Vue 3 migration
// This replaces the Vue 2 pattern of using $on/$off/$once on Vue instances
export const eventBus = mitt();