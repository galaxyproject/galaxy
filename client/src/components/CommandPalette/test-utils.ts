import type { PaletteContext, ScopedSection } from "./types";

/** A logged-in palette context with every optional feature off; `overrides` replace whole fields */
export function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAnonymous: false, ...overrides };
}

/** The sections the palette renders of a scoped answer, which drops the empty ones */
export function renderedSections(sections: ScopedSection[] = []): ScopedSection[] {
    return sections.filter((section) => section.items.length > 0);
}
