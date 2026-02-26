// Type declarations for jsondiffpatch subpath exports
declare module "jsondiffpatch/formatters/html" {
    import type { Delta } from "jsondiffpatch"
    export function format(delta: Delta, left?: unknown): string | undefined
    export const showUnchanged: (show?: boolean, node?: Element | null, delay?: number) => void
    export const hideUnchanged: (node?: Element, delay?: number) => void
}
