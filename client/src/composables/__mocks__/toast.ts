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
