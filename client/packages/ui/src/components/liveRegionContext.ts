import type { InjectionKey } from "vue";

/** True below a component that is already a live region, so nested content can skip its own role. */
export const liveRegionKey: InjectionKey<boolean> = Symbol("g-live-region");
