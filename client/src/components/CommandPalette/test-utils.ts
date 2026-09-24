import type { PaletteContext } from "./types";

/** A logged-in palette context with every optional feature off; `overrides` replace whole fields */
export function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAnonymous: false, ...overrides };
}
