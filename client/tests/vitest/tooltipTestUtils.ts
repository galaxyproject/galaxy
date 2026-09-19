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

export async function runPendingTimersAndFlush() {
    vi.runOnlyPendingTimers();
    await nextTick();
}
