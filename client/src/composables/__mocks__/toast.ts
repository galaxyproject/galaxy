import type { ToastProps } from "@galaxyproject/galaxy-ui";
import { vi } from "vitest";
import { readonly, ref } from "vue";

/**
 * Manual mock for `@/composables/toast`, opted into per file with `vi.mock("@/composables/toast")`.
 *
 * Real toasts are a singleton: `Toast` is just `useToast()`, and both paths reach the same queue.
 * A per-file inline mock usually hands the two paths separate spies, so `expect(...).not
 * .toHaveBeenCalled()` passes against whichever path the component did not happen to use. Here
 * they are one object, so that assertion means what it says.
 *
 * Assert through the same import production code uses - `import { Toast } from "@/composables/toast"`
 * or `useToast()` - and reset between tests with `vi.clearAllMocks()`.
 */
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

/** The notify methods, in no particular order - `raisedToasts` sorts by when they were called. */
const VARIANTS = ["error", "info", "success", "warning"] as const;

export type ToastVariantCall = { variant: (typeof VARIANTS)[number]; message: unknown };

/**
 * Every toast raised so far, oldest first, for the tests that care about the sequence *across*
 * variants ("a success, then an info") rather than about one method's calls. Order comes from the
 * spies themselves, so `vi.clearAllMocks()` empties this too and there is no second thing to reset.
 */
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

/** Forget every recorded toast. `vi.clearAllMocks()` covers this; use it when a test deliberately
 *  clears only some of its mocks. */
export function clearRaisedToasts() {
    VARIANTS.forEach((variant) => Toast[variant].mockClear());
}
