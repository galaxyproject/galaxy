declare module "@vue/compat" {
    export * from "vue";
    export { default } from "vue";

    export function configureCompat(config: { MODE?: 2 | 3; [key: string]: unknown }): void;
}
