import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeMonitoringData } from "@tests/test-data/monitoring";
import { expect, fn, waitFor, within } from "storybook/test";
import { h, markRaw, ref } from "vue";

import type { TaskMonitor } from "@/composables/genericTaskMonitor";
import { getPersistentKey, type MonitoringRequest } from "@/composables/persistentProgressMonitor";

import PersistentTaskProgressMonitorAlert from "./PersistentTaskProgressMonitorAlert.vue";

const DAY = 24 * 60 * 60 * 1000;
const TASK_ID = "6f1c2a4e-8d3b-4f7a-9c05-2e8b7d1a3f60";
const DOWNLOAD_REQUEST_ID = "c94e7b12-05a3-4d8e-b6f1-7a2d9e3c4b58";

/** What the invocation export wizard asks to monitor when exporting to a remote file source. */
const REMOTE_EXPORT: MonitoringRequest = {
    source: "wizard",
    action: "export",
    taskType: "task",
    object: { id: "f2db41e1fa331b3e", type: "invocation", name: "RNA-seq alignment" },
    description: "Invocation export for workflow RNA-seq alignment to remote source",
};

/** The same export prepared for direct download. */
const DOWNLOAD_EXPORT: MonitoringRequest = {
    ...REMOTE_EXPORT,
    taskType: "short_term_storage",
    description: "Invocation export for workflow RNA-seq alignment for direct download",
};

/**
 * A task monitor already in the given state, which never polls. Its results expire after a
 * day, as Galaxy's monitors do. Raw, so Storybook's reactive args don't unwrap its refs.
 */
function taskMonitor(state: Partial<TaskMonitor> = {}): TaskMonitor {
    return markRaw({
        waitForTask: async () => {},
        stopWaitingForTask: () => {},
        isRunning: ref(false),
        isCompleted: ref(false),
        hasFailed: ref(false),
        failureReason: ref(),
        requestHasFailed: ref(false),
        taskStatus: ref(),
        isFinalState: () => false,
        loadStatus: () => {},
        fetchTaskStatus: async () => {},
        expirationTime: DAY,
        ...state,
    });
}

interface StoredTask {
    taskId: string;
    /** How long ago the task started, in milliseconds. */
    startedAgo?: number;
}

/** Story parameters for a task some page started earlier and stored. */
function storedTask(task: StoredTask) {
    return { storedTask: task };
}

/**
 * The alert shows a task some page started earlier and stored in local storage. Store the
 * story's `storedTask` parameter there before the alert reads it, or clear it.
 */
const withStoredTask: Decorator = (story, { args, parameters }) => ({
    setup() {
        const request = args.monitorRequest as MonitoringRequest;
        const key = getPersistentKey(request);
        const task: StoredTask | undefined = parameters.storedTask;
        if (task) {
            const startedAt = new Date(Date.now() - (task.startedAgo ?? 0));
            const data = getFakeMonitoringData(request, { taskId: task.taskId, startedAt });
            localStorage.setItem(key, JSON.stringify(data));
        } else {
            localStorage.removeItem(key);
        }
    },
    render: () => h(story()),
});

const meta = {
    title: "Common/PersistentTaskProgressMonitorAlert",
    component: PersistentTaskProgressMonitorAlert,
    decorators: [withStoredTask],
    // Both are read once, when the alert is created, so editing them live shows nothing.
    argTypes: { monitorRequest: { control: false }, useMonitor: { control: false } },
    args: {
        monitorRequest: REMOTE_EXPORT,
        useMonitor: taskMonitor(),
        onOnDismiss: fn(),
    },
} satisfies Meta<typeof PersistentTaskProgressMonitorAlert>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/**
 * A completed result's expiry, a day after the task started. Across a daylight-saving change
 * the browser's clock reads that day as 23 or 25 hours.
 */
const EXPIRES_IN_A_DAY = "This result will expire in (1 day|about 2[345] hours)";

/**
 * Reads the alert's whole text, then `expiry` (a pattern) when given. A dismissible alert ends
 * with its close button's "×". Info and success alerts are a `status`; danger and warning ones
 * an `alert`.
 */
async function seeAlert(
    { canvas, step }: PlayContext,
    role: "status" | "alert",
    text: string,
    { dismissible = true, expiry }: { dismissible?: boolean; expiry?: string } = {},
) {
    let alert!: HTMLElement;
    await step(`See "${text}"${expiry ? " and when the result expires" : ""}`, async () => {
        alert = await canvas.findByRole(role);
        const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const pattern = `^${escaped}${expiry ? ` ${expiry}` : ""}${dismissible ? " ×" : ""}$`;
        await expect(alert).toHaveTextContent(new RegExp(pattern));
    });
    return alert;
}

/** No task was started from this page, so there is nothing to show. */
export const NoTaskStarted: Story = {};

export const InProgress: Story = {
    args: { useMonitor: taskMonitor({ isRunning: ref(true) }) },
    parameters: storedTask({ taskId: TASK_ID }),
    play: async (context) => {
        await seeAlert(context, "status", "Task is in progress. Please wait...", { dismissible: false });
    },
};

export const Completed: Story = {
    args: { useMonitor: taskMonitor({ isCompleted: ref(true) }) },
    parameters: storedTask({ taskId: TASK_ID }),
    play: async (context) => {
        await seeAlert(context, "status", "Task completed successfully.", { expiry: EXPIRES_IN_A_DAY });
        await context.step("See no download link for a task that isn't a download", async () => {
            await expect(context.canvas.queryByRole("link")).not.toBeInTheDocument();
        });
    },
};

/** Closing a finished task's alert hides it and tells the page. */
export const DismissesCompleted: Story = {
    ...Completed,
    play: async (context) => {
        const alert = await seeAlert(context, "status", "Task completed successfully.", { expiry: EXPIRES_IN_A_DAY });
        await context.step("Close the alert; it goes away", async () => {
            await expect(context.args.onOnDismiss).not.toHaveBeenCalled();
            await context.userEvent.click(within(alert).getByRole("button", { name: "Close" }));
            await waitFor(() => expect(context.canvas.queryByRole("status")).not.toBeInTheDocument());
            await expect(context.args.onOnDismiss).toHaveBeenCalledTimes(1);
        });
    },
};

/** A short-term storage result links to its download until it expires. */
export const DownloadReady: Story = {
    args: { monitorRequest: DOWNLOAD_EXPORT, useMonitor: taskMonitor({ isCompleted: ref(true) }) },
    parameters: storedTask({ taskId: DOWNLOAD_REQUEST_ID }),
    play: async (context) => {
        const alert = await seeAlert(context, "status", "Task completed successfully. Download here", {
            expiry: EXPIRES_IN_A_DAY,
        });
        await context.step("See the link to download the result", async () => {
            await expect(within(alert).getByRole("link", { name: "Download here" })).toHaveAttribute(
                "href",
                `/api/short_term_storage/${DOWNLOAD_REQUEST_ID}`,
            );
        });
    },
};

export const Failed: Story = {
    args: {
        useMonitor: taskMonitor({
            hasFailed: ref(true),
            failureReason: ref("The remote file source rejected the upload"),
        }),
    },
    parameters: storedTask({ taskId: TASK_ID }),
    play: async (context) => {
        await seeAlert(context, "alert", "Task failed. Reason: The remote file source rejected the upload");
    },
};

/** Started two days ago: the result is gone, even though the last status seen was running. */
export const Expired: Story = {
    args: { useMonitor: taskMonitor({ isRunning: ref(true) }) },
    parameters: storedTask({ taskId: TASK_ID, startedAgo: 2 * DAY }),
    play: async (context) => {
        await seeAlert(context, "alert", "The export task has expired and the result is no longer available.");
    },
};
