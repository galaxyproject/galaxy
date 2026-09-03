import { readonly, ref } from "vue";

import type { ColorVariant } from "../components/componentVariants";

export type ToastVariant = Extract<ColorVariant, "success" | "info" | "warning" | "danger">;

export interface ToastOptions {
    /** Optional heading shown above the message. */
    title?: string;
    /** Contextual colour of the toast. */
    variant?: ToastVariant;
    /** If set, clicking the toast navigates here. Must be a fully-resolved URL. */
    href?: string;
    /** Internal site route to navigate to on click. Uses the internal router. */
    to?: string;
    /** Milliseconds before the toast auto-dismisses. `0` disables auto-dismiss. */
    duration?: number;
}

export interface ToastProps extends Required<Omit<ToastOptions, "href">> {
    id: number;
    message: string;
    href: string;
}

const TITLE_DEFAULTS = {
    success: "Success",
    info: "Info",
    warning: "Warning",
    danger: "Error",
} as const;

const DEFAULT_DURATION = 3000;

// Toasts are a singleton: every caller pushes onto the same queue, which the
// single mounted `<GToast>` host renders. The state and helpers therefore live
// at file level (created once) rather than per `useToast()` call.
const queue = ref<ToastProps[]>([]);

/**
 * Exposed read-only so callers mutate only via `addToast`/`removeToast`/`clearToasts`,
 * which also manage the auto-dismiss timers.
 */
const toasts = readonly(queue);
const timers = new Map<number, ReturnType<typeof setTimeout>>();

/** The next toast id to assign. */
let nextId = 0;

/** Remove a toast from the queue by id. */
function removeToast(id: number): void {
    const timer = timers.get(id);
    if (timer) {
        clearTimeout(timer);
        timers.delete(id);
    }

    const index = queue.value.findIndex((toast) => toast.id === id);
    if (index !== -1) {
        queue.value.splice(index, 1);
    }
}

/** Add a toast to the queue. Returns its generated id. */
function addToast(message: string, options: ToastOptions = {}): number {
    const id = nextId++;

    const toast: ToastProps = {
        id,
        message,
        title: options.title ?? TITLE_DEFAULTS[options.variant ?? "info"],
        variant: options.variant ?? "info",
        href: options.href ?? "",
        to: options.to ?? "",
        duration: options.duration ?? DEFAULT_DURATION,
    };

    queue.value.push(toast);

    if (toast.duration > 0) {
        timers.set(
            id,
            setTimeout(() => removeToast(id), toast.duration),
        );
    }

    return id;
}

/** Remove every queued toast. */
function clearToasts(): void {
    for (const timer of timers.values()) {
        clearTimeout(timer);
    }
    timers.clear();
    queue.value.splice(0, queue.value.length);
}

// Simplified methods to use to raise toasts (for passing more props, use `addToast` directly).
function success(message: string, title?: string) {
    addToast(message, { title, variant: "success" });
}
function info(message: string, title?: string) {
    addToast(message, { title, variant: "info" });
}
function warning(message: string, title?: string) {
    addToast(message, { title, variant: "warning" });
}
function error(message: string, title?: string) {
    addToast(message, { title, variant: "danger" });
}

/**
 * Access the global toast queue and helpers.
 *
 * `success` / `info` / `warning` / `error` raise a toast of that variant with
 * a sensible default title. Use `addToast` for full control, `removeToast` /
 * `clearToasts` to dismiss.
 */
export function useToast() {
    return {
        toasts,
        addToast,
        clearToasts,
        error,
        info,
        removeToast,
        success,
        warning,
    };
}
