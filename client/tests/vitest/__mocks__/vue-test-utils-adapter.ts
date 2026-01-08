/**
 * Vue Test Utils v1 → v2 Compatibility Adapter
 *
 * This wrapper transforms old Vue Test Utils v1 mount options to v2 format,
 * allowing existing tests to work without modification.
 *
 * Patterns handled:
 * - { global: localVue, pinia, router } → { global: { ...localVue, plugins: [pinia, router] } }
 * - { localVue, pinia, router } → { global: { ...localVue, plugins: [pinia, router] } }
 */
// Import from the actual node_modules path to avoid circular alias resolution
// @ts-ignore - Direct path import
import * as VTU from "../../../node_modules/@vue/test-utils/dist/vue-test-utils.esm-bundler.mjs";

// Check if a plugin is a Pinia instance
function isPinia(plugin: any): boolean {
    return plugin && typeof plugin === "object" && "_s" in plugin && "_e" in plugin;
}

// Check if a plugin is a Router instance
function isRouter(plugin: any): boolean {
    return plugin && typeof plugin === "object" && "currentRoute" in plugin && "push" in plugin;
}

function adaptMountOptions(options: Record<string, any> = {}): Record<string, any> {
    const normalized = { ...options };
    const pluginsToAdd: any[] = [];

    // Move top-level pinia to plugins (if not already present)
    if (normalized.pinia) {
        pluginsToAdd.push(normalized.pinia);
        delete normalized.pinia;
    }

    // Move top-level router to plugins (if not already present)
    if (normalized.router) {
        pluginsToAdd.push(normalized.router);
        delete normalized.router;
    }

    // Handle old Vue 2 localVue option (convert to global)
    if (normalized.localVue) {
        if (normalized.global) {
            // Merge localVue into existing global
            normalized.global = { ...normalized.localVue, ...normalized.global };
        } else {
            normalized.global = normalized.localVue;
        }
        delete normalized.localVue;
    }

    // Add collected plugins to global.plugins, avoiding duplicates
    if (pluginsToAdd.length > 0) {
        normalized.global = normalized.global ?? {};
        const existingPlugins = normalized.global.plugins ?? [];

        // Filter out plugins that would be duplicates
        const filteredPluginsToAdd = pluginsToAdd.filter((plugin) => {
            // Check if a Pinia instance already exists
            if (isPinia(plugin)) {
                return !existingPlugins.some(isPinia);
            }
            // Check if a Router instance already exists
            if (isRouter(plugin)) {
                return !existingPlugins.some(isRouter);
            }
            // For other plugins, add them
            return true;
        });

        normalized.global.plugins = [...existingPlugins, ...filteredPluginsToAdd];
    }

    return normalized;
}

// Wrapped mount function
export const mount: typeof VTU.mount = (component: any, options?: any) => {
    return VTU.mount(component, adaptMountOptions(options));
};

// Wrapped shallowMount function
export const shallowMount: typeof VTU.shallowMount = (component: any, options?: any) => {
    return VTU.shallowMount(component, adaptMountOptions(options));
};

// Re-export everything else from @vue/test-utils unchanged
export const {
    config,
    enableAutoUnmount,
    disableAutoUnmount,
    flushPromises,
    DOMWrapper,
    VueWrapper,
    BaseWrapper,
    RouterLinkStub,
    createWrapperError,
} = VTU;

// Default export for compatibility
export default {
    mount,
    shallowMount,
    config: VTU.config,
    enableAutoUnmount: VTU.enableAutoUnmount,
    disableAutoUnmount: VTU.disableAutoUnmount,
    flushPromises: VTU.flushPromises,
    DOMWrapper: VTU.DOMWrapper,
    VueWrapper: VTU.VueWrapper,
    RouterLinkStub: VTU.RouterLinkStub,
};
