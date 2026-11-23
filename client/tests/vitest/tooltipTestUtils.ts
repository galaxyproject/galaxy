import flushPromises from "flush-promises";
import { vi } from "vitest";
import { nextTick } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

export function advanceToJustBeforeTooltipHoverDelay(delayMs = DEFAULT_TOOLTIP_HOVER_DELAY_MS) {
    vi.advanceTimersByTime(delayMs - 1);
}

export async function advanceTooltipHoverDelay(delayMs = 1) {
    vi.advanceTimersByTime(delayMs);
    await nextTick();
}

/** Hovers the element for as long as tooltips and popovers wait before opening. */
export async function hoverPastTooltipDelay(element: { trigger(eventName: string): Promise<unknown> }) {
    vi.useFakeTimers();
    try {
        await element.trigger("mouseenter");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
    } finally {
        vi.useRealTimers();
    }
    await flushPromises();
}

export async function runPendingTimersAndFlush() {
    vi.runOnlyPendingTimers();
    await nextTick();
}
