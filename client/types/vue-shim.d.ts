declare module "*.vue" {
    import type { DefineComponent } from "vue";
    const component: DefineComponent<{}, {}, any>;
    export default component;
}

// Compatibility type exports
declare module "vue" {
    export interface ComponentCustomProperties {
        // Add custom properties here if needed
    }
}