export { iconMixin, iconPlugin } from "./icons";
export { localizationPlugin } from "./localization";
export { vueRxShortcutPlugin, vueRxShortcuts } from "./vueRxShortcuts";

// I'm explicitly ommitting this because of its ugly dependencies, I want us to have to import the
// legacy nav features manually (when required) rather than it coming in every time somebody accesses
// the plugin module/index.js
// export { legacyNavigationMixin, legacyNavigationPlugin } from "./legacyNavigation";
