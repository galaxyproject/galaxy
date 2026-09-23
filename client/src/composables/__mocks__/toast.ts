import type { ToastProps } from "@galaxyproject/galaxy-ui";
import { vi } from "vitest";
import { readonly, ref } from "vue";

// Opt in per file with `vi.mock("@/composables/toast")`; reset with `vi.clearAllMocks()`.
// `Toast` and `useToast()` are one object, as in production - separate spies would let an
// assertion that no toast fired pass against whichever path the component did not take.
export const Toast = {
    toasts: readonly(ref<ToastProps[]>([])),
    addToast: vi.fn(),
    clearToasts: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    removeToast: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
};

export const useToast = vi.fn(() => Toast);

const VARIANTS = ["error", "info", "success", "warning"] as const;

export type ToastVariantCall = { variant: (typeof VARIANTS)[number]; message: unknown };

/** Every toast raised so far, oldest first, for tests asserting a sequence across variants. */
export function raisedToasts(): ToastVariantCall[] {
    return VARIANTS.flatMap((variant) =>
        Toast[variant].mock.calls.map((args, index) => ({
            order: Toast[variant].mock.invocationCallOrder[index] ?? 0,
            variant,
            message: args[0] as unknown,
        })),
    )
        .sort((a, b) => a.order - b.order)
        .map(({ variant, message }) => ({ variant, message }));
}

/** For tests clearing only some of their mocks; `vi.clearAllMocks()` covers this too. */
export function clearRaisedToasts() {
    VARIANTS.forEach((variant) => Toast[variant].mockClear());
}
