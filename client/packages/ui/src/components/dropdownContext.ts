import type { InjectionKey } from "vue";

/** Closes the enclosing dropdown menu; `restoreFocus` (default true) moves focus back to its toggle. */
export const dropdownHideKey: InjectionKey<(restoreFocus?: boolean) => void> = Symbol("g-dropdown-hide");
