// Vue SFC module declaration
declare module "*.vue" {
    import type { DefineComponent } from "@vue/runtime-core";
    const component: DefineComponent<{}, {}, any>;
    export default component;
}

// Re-export all Vue types from @vue/compat for proper type resolution
declare module "vue" {
    export * from "@vue/runtime-dom";
    export * from "@vue/runtime-core";
    export * from "@vue/reactivity";
    export * from "@vue/shared";
    
    // Add any custom properties to components here
    export interface ComponentCustomProperties {
        // Custom properties can be added here if needed
    }
}