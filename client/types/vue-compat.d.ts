declare module "@vue/compat" {
    import type { Plugin } from "vue";

    export * from "vue";

    export function configureCompat(config: { MODE?: 2 | 3; [key: string]: unknown }): void;

    /**
     * The compat build's default export keeps the Vue 2 style global API
     * (`Vue.use(...)`) for the handful of components that install a plugin
     * (e.g. BootstrapVue) globally instead of through an app instance.
     */
    interface CompatVueGlobal {
        use<Options extends unknown[]>(plugin: Plugin<Options>, ...options: Options): CompatVueGlobal;
    }
    const Vue: CompatVueGlobal;
    export default Vue;
}
