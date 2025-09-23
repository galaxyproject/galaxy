// https://github.com/vueuse/vueuse/blob/main/packages/core/_configurable.ts
import type { ConfigurableWindow, MaybeElementRef, UseFocusWithinReturn } from "@vueuse/core";
import { unrefElement, useEventListener } from "@vueuse/core";
import { computedWithControl, isClient } from "@vueuse/shared";
import { computed } from "vue";

const defaultWindow = isClient ? window : undefined;

/**
 * Reactive `document.activeElement`
 *
 * @see https://vueuse.org/useActiveElement
 * @param options
 */
export function useActiveElement<T extends HTMLElement>(options: ConfigurableWindow = {}) {
    const { window = defaultWindow } = options;
    const activeElement = computedWithControl(
        () => null,
        () => window?.document.activeElement as T | null | undefined
    );

    if (window) {
        useEventListener(
            window,
            "blur",
            () => {
                const scheduler = window.requestAnimationFrame || window.setTimeout;
                scheduler(() => activeElement.trigger());
            },
            true
        );
        useEventListener(window, "focus", activeElement.trigger, true);
    }
    return activeElement;
}

/**
 * Track if focus is contained within the target element
 *
 * @see https://vueuse.org/useFocusWithin
 * @param target The target element to track
 * @param options Focus within options
 */
export function useFocusWithin(target: MaybeElementRef, options: ConfigurableWindow = {}): UseFocusWithinReturn {
    const activeElement = useActiveElement(options);
    const targetElement = computed(() => unrefElement(target));
    const focused = computed(() =>
        targetElement.value && activeElement.value ? targetElement.value.contains(activeElement.value) : false
    );

    return { focused };
}
