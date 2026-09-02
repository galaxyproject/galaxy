import { readonly, ref } from "vue";

import type { ColorVariant } from "../components/componentVariants";

export type ToastVariant = Extract<ColorVariant, "success" | "info" | "warning" | "danger">;

export interface ToastOptions {
    /** Optional heading shown above the message. */
    title?: string;
    /** Contextual colour of the toast. */
    variant?: ToastVariant;
    /** If set, clicking the toast navigates here. */
    href?: string;
    /** Milliseconds before the toast auto-dismisses. `0` disables auto-dismiss. */
    duration?: number;
}

export interface ToastProps extends Required<Omit<ToastOptions, "href">> {
    id: number;
    message: string;
    href: string;
}

const DEFAULT_DURATION = 3000;

// Toasts are a singleton: every caller pushes onto the same queue, which the
// single mounted `<GToast>` host renders. The state therefore lives at file
// level (created once) rather than per `useToast()` call.
const queue = ref<ToastProps[]>([]);

/**
 * Exposed read-only so callers mutate only via `addToast`/`removeToast`/`clearToasts`,
 * which also manage the auto-dismiss timers.
 */
const readonlyQueue = readonly(queue);
const timers = new Map<number, ReturnType<typeof setTimeout>>();

/**
 * The next toast id to assign. Incremented on each `addToast` and reduced on each
 * `removeToast` to avoid unbounded growth.
 */
let nextId = 0;

/**
 * Access the global toast queue and helpers.
 *
 * `success` / `info` / `warning` / `error` raise a toast of that variant with
 * a sensible default title. Use `addToast` for full control, `removeToast` /
 * `clearToasts` to dismiss.
 */
export function useToast() {
    /** Read-only ref of the current toast queue, for rendering. */
    const toasts = readonlyQueue;

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
            title: options.title ?? "",
            variant: options.variant ?? "info",
            href: options.href ?? "",
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

    // Main methods to use to raise toasts
    function success(message: string, title = "Success", href = "") {
        addToast(message, { title, variant: "success", href });
    }
    function info(message: string, title = "Info", href = "") {
        addToast(message, { title, variant: "info", href });
    }
    function warning(message: string, title = "Warning", href = "") {
        addToast(message, { title, variant: "warning", href });
    }
    function error(message: string, title = "Error", href = "") {
        addToast(message, { title, variant: "danger", href });
    }

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
