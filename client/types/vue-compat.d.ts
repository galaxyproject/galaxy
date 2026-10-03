declare module "@vue/compat" {
    import type { AppConfig, ComponentOptions, Plugin } from "vue";

    export * from "vue";

    export function configureCompat(config: { MODE?: 2 | 3; [key: string]: unknown }): void;

    /**
     * The compat build's default export keeps the Vue 2 style global API
     * (`Vue.use(...)`, `Vue.mixin(...)`) for the handful of call sites that
     * still install things globally instead of through an app instance.
     */
    interface CompatVueGlobal {
        config: AppConfig;
        use<Options extends unknown[]>(plugin: Plugin<Options>, ...options: Options): CompatVueGlobal;
        mixin(mixin: ComponentOptions): CompatVueGlobal;
    }
    const Vue: CompatVueGlobal;
    export default Vue;
}
