declare module "@vue/compat" {
    export * from "@vue/runtime-dom";
    export { default } from "@vue/runtime-dom";

    export function configureCompat(config: { MODE?: 2 | 3; [key: string]: any }): void;

    export function createApp(...args: any[]): any;
}
