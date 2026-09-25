// DOMPurify does not produce reliable output under happy-dom, so unit tests
// get a pass-through spy: components can assert what they send to the
// sanitizer and that its result is what ends up in the DOM.
import { vi } from "vitest";

export const sanitizeHtml = vi.fn((html: string | null | undefined) => html ?? "");
