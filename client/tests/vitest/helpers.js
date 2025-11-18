/**
 * Unit test debugging utilities for Vitest
 */
import { vi } from "vitest";

export function suppressDebugConsole() {
    vi.spyOn(console, "debug").mockImplementation(vi.fn());
}

export function suppressBootstrapVueWarnings() {
    const originalWarn = console.warn;
    vi.spyOn(console, "warn").mockImplementation(
        vi.fn((msg) => {
            if (msg.indexOf("BootstrapVue warn") < 0) {
                originalWarn(msg);
            }
        }),
    );
}

export function suppressErrorForCustomIcons() {
    const originalError = console.error;
    vi.spyOn(console, "error").mockImplementation(
        vi.fn((msg) => {
            if (msg.indexOf("Could not find one or more icon(s)") < 0) {
                originalError(msg);
            }
        }),
    );
}

export function suppressLucideVue2Deprecation() {
    const originalWarn = console.warn;
    vi.spyOn(console, "warn").mockImplementation(
        vi.fn((msg) => {
            if (msg.indexOf("[Lucide Vue] This package will be deprecated") < 0) {
                originalWarn(msg);
            }
        }),
    );
}
