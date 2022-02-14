export { eventHubMixin, eventHubPlugin } from "./eventHub";
export { vueRxShortcutPlugin, vueRxShortcuts } from "./vueRxShortcuts";
export { localizationPlugin } from "./localization";
export { iconPlugin, iconMixin } from "./icons";

// I'm explicitly ommitting this because of its ugly dependencies, I want us to have to import the
// legacy nav features manually (when required) rather than it coming in every time somebody accesses
// the plugin module/index.js
// export { legacyNavigationMixin, legacyNavigationPlugin } from "./legacyNavigation";
