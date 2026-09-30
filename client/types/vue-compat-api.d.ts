// "vue" is aliased to @vue/compat at build time, and the compat build exports
// configureCompat. The real vue types declare it but don't export it. This file is
// a module (see the export below), so the block augments "vue" rather than
// replacing its types.
export {};

declare module "vue" {
    export function configureCompat(config: { MODE?: 2 | 3; [key: string]: unknown }): void;
}
