import { getFakeRegisteredUser } from "@tests/test-data";

import { useUserStore } from "@/stores/userStore";

import type { PaletteContext, ScopedSection } from "./types";

/** A logged-in palette context with every optional feature off; `overrides` replace whole fields */
export function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAnonymous: false, ...overrides };
}

/** The sections the palette renders of a scoped answer, which drops the empty ones */
export function renderedSections(sections: ScopedSection[] = []): ScopedSection[] {
    return sections.filter((section) => section.items.length > 0);
}

/** Signs `username` in on the active pinia, so ownership checks compare rows against it */
export function signIn(username = "me") {
    useUserStore().currentUser = getFakeRegisteredUser({ id: "user-1", email: "me@example.org", username });
}
