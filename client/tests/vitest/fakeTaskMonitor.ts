import { vi } from "vitest";
import { ref } from "vue";

import type { TaskMonitor } from "@/composables/genericTaskMonitor";

/** An idle task monitor with fresh refs and spy methods; override the state a test needs. */
export function getFakeTaskMonitor(overrides: Partial<TaskMonitor> = {}): TaskMonitor {
    return {
        waitForTask: vi.fn(),
        stopWaitingForTask: vi.fn(),
        isRunning: ref(false),
        isCompleted: ref(false),
        hasFailed: ref(false),
        failureReason: ref(),
        requestHasFailed: ref(false),
        taskStatus: ref(),
        isFinalState: vi.fn(),
        loadStatus: vi.fn(),
        fetchTaskStatus: vi.fn(),
        ...overrides,
    };
}
