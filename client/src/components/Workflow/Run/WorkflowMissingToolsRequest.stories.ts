import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import { configurationHandler, http } from "@/api/client/__mocks__/http";

import WorkflowMissingToolsRequest from "./WorkflowMissingToolsRequest.vue";

/** The request needs both the form and the notification system that delivers it to admins. */
const REQUESTS_ENABLED = { enable_notification_system: true, enable_tool_installation_request_form: true };

/** Galaxy accepts the request and notifies the admins. */
const requestSent = http.post("/api/notifications", ({ response }) =>
    response.untyped(HttpResponse.json({ total_notifications_sent: 1, notification: {} })),
);

const meta = {
    title: "Workflow/Run/WorkflowMissingToolsRequest",
    component: WorkflowMissingToolsRequest,
    decorators: [withCurrentUser()],
    args: {
        missingToolIds: [
            "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
            "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13",
        ],
        workflowId: "f2db41e1fa331b3e",
    },
    parameters: {
        msw: { handlers: { configuration: configurationHandler(REQUESTS_ENABLED), notifications: requestSent } },
    },
} satisfies Meta<typeof WorkflowMissingToolsRequest>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Waits for the request button, which shows once the config has loaded; `label` is its whole name. */
async function seeRequestButton({ canvas, step }: PlayContext, label: string) {
    let button!: HTMLElement;
    await step(`See the "${label}" button`, async () => {
        button = await canvas.findByRole("button", { name: label });
        await expect(button).toBeVisible();
    });
    return button;
}

/** Opens the request dialog from the button, checking it was closed before. */
async function openRequestDialog(context: PlayContext, label = "Request Installation (2 missing tools)") {
    const button = await seeRequestButton(context, label);
    let dialog!: HTMLElement;
    await context.step("Open the request dialog", async () => {
        await expect(context.canvas.queryByRole("dialog")).not.toBeInTheDocument();
        await context.userEvent.click(button);
        dialog = await context.canvas.findByRole("dialog");
        await expect(within(dialog).getByRole("heading", { name: "Request Tool Installation" })).toBeVisible();
    });
    return dialog;
}

/** Checks the dialog's question names how many tools are requested. */
async function seeQuestion(dialog: HTMLElement, tools: string) {
    await expect(within(dialog).getByRole("strong")).toHaveTextContent(new RegExp(`^${tools}$`));
    await expect(within(dialog).getAllByRole("paragraph")[0]).toHaveTextContent(
        new RegExp(`^Request the admins to install ${tools} required by this workflow\\?$`),
    );
}

async function clickDialogButton({ userEvent }: PlayContext, dialog: HTMLElement, name: string) {
    await userEvent.click(within(dialog).getByRole("button", { name }));
}

async function seeDialogClosed({ canvas }: PlayContext) {
    await waitFor(() => expect(canvas.queryByRole("dialog")).not.toBeInTheDocument());
}

/**
 * Cancels the dialog. The dialog hides at once but tells the component in a later `close`
 * event, so wait for that before reopening, or the reopen click lands on stale state.
 */
async function cancelDialog(context: PlayContext, dialog: HTMLElement) {
    await context.step("Cancel; the dialog closes", async () => {
        const closed = new Promise((resolve) => dialog.addEventListener("close", resolve, { once: true }));
        await clickDialogButton(context, dialog, "Cancel");
        await closed;
        await seeDialogClosed(context);
    });
}

/** The workflow uses two tools this Galaxy hasn't installed; the user can ask the admins for them. */
export const MissingTools: Story = {
    play: async (context) => {
        await seeRequestButton(context, "Request Installation (2 missing tools)");
    },
};

/** Just one tool is missing. */
export const OneMissingTool: Story = {
    args: { missingToolIds: ["toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"] },
    play: async (context) => {
        await seeRequestButton(context, "Request Installation (1 missing tool)");
    },
};

/** The dialog asks about the single missing tool, with no note about a limit. */
export const AsksForOneTool: Story = {
    ...OneMissingTool,
    play: async (context) => {
        const dialog = await openRequestDialog(context, "Request Installation (1 missing tool)");
        await context.step('See the dialog ask about "1 missing tool"', async () => {
            await seeQuestion(dialog, "1 missing tool");
            await expect(within(dialog).queryByText(/Only the first/)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** More tools are missing than one request can carry; the dialog says only the first 50 are sent. */
export const OverRequestLimit: Story = {
    args: { missingToolIds: Array.from({ length: 60 }, (_, i) => `tool-${i}`) },
};

/** Opening the over-limit request, the dialog says which tools will be sent. */
export const NotesTruncatedRequest: Story = {
    ...OverRequestLimit,
    play: async (context) => {
        const dialog = await openRequestDialog(context, "Request Installation (60 missing tools)");
        await context.step("See that only the first 50 tools will be requested", async () => {
            await seeQuestion(dialog, "60 missing tools");
            await expect(within(dialog).getByText(/^Only the first/)).toHaveTextContent(
                /^Only the first 50 of the 60 missing tools will be included in the request\.$/,
            );
        });
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Cancelling closes the dialog without sending; the button opens it again. */
export const CancelsAndReopens: Story = {
    play: async (context) => {
        const dialog = await openRequestDialog(context);
        await cancelDialog(context, dialog);
        await openRequestDialog(context);
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Sending the request closes the dialog and swaps the button for a confirmation. */
export const SendsRequest: Story = {
    play: async (context) => {
        const dialog = await openRequestDialog(context);
        await context.step("Send the request; see it confirmed", async () => {
            await clickDialogButton(context, dialog, "Send Request");
            await expect(await context.canvas.findByRole("alert")).toHaveTextContent(
                /^Installation request sent\. Check your notifications for updates\.$/,
            );
        });
        await context.step("See the dialog closed and the button gone", async () => {
            await seeDialogClosed(context);
            await expect(
                context.canvas.queryByRole("button", { name: /Request Installation/ }),
            ).not.toBeInTheDocument();
        });
    },
};

/** Answers the request held by `requestHeld`; the play sets it when the request arrives. */
let answerHeldRequest: (() => void) | undefined;

/** Galaxy takes the request but holds its answer until the play calls `answerHeldRequest`. */
const requestHeld = http.post("/api/notifications", async ({ response }) => {
    await new Promise<void>((resolve) => {
        answerHeldRequest = resolve;
    });
    return response.untyped(HttpResponse.json({ total_notifications_sent: 1, notification: {} }));
});

/** While Galaxy is still taking the request, neither button can send it again. */
export const DisablesWhileSending: Story = {
    parameters: { msw: { handlers: { notifications: requestHeld } } },
    play: async (context) => {
        const dialog = await openRequestDialog(context);
        const send = within(dialog).getByRole("button", { name: "Send Request" });
        await context.step("Send the request; both buttons wait for Galaxy's answer", async () => {
            await expect(send).not.toHaveAttribute("aria-disabled");
            await context.userEvent.click(send);
            await waitFor(() => expect(answerHeldRequest).toBeDefined());
            await expect(send).toHaveAttribute("aria-disabled", "true");
            await expect(
                context.canvas.getByRole("button", { name: "Request Installation (2 missing tools)" }),
            ).toHaveAttribute("aria-disabled", "true");
        });
        await context.step("Galaxy answers; see the request confirmed", async () => {
            answerHeldRequest?.();
            answerHeldRequest = undefined;
            await expect(await context.canvas.findByRole("alert")).toHaveTextContent(/^Installation request sent\./);
        });
    },
};

/** Galaxy will refuse the request; once sent, the error shows inside the still-open dialog. */
export const RequestFails: Story = {
    parameters: {
        msw: {
            handlers: {
                notifications: http.post("/api/notifications", ({ response }) =>
                    response("5XX").json({ err_msg: "Server error", err_code: 500 }, { status: 500 }),
                ),
            },
        },
    },
};

/** Sends the failing request and returns the error alert shown in the dialog. */
async function seeRequestFail(context: PlayContext, dialog: HTMLElement) {
    let alert!: HTMLElement;
    await context.step("Send the request; see Galaxy's error in the dialog", async () => {
        await clickDialogButton(context, dialog, "Send Request");
        // The alert is dismissible; its close button's "×" comes first.
        alert = await within(dialog).findByRole("alert");
        await expect(alert).toHaveTextContent(/^×Server error$/);
    });
    return alert;
}

/**
 * A refused request keeps the dialog open with the error inside it: the open dialog makes the
 * rest of the page inert, so an alert outside it couldn't be read.
 */
export const ShowsErrorInDialog: Story = {
    ...RequestFails,
    play: async (context) => {
        const dialog = await openRequestDialog(context);
        await seeRequestFail(context, dialog);
        await context.step("See the dialog still open and the button still there", async () => {
            await expect(context.canvas.getByRole("dialog")).toBe(dialog);
            await expect(
                context.canvas.getByRole("button", { name: "Request Installation (2 missing tools)" }),
            ).toBeInTheDocument();
        });
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { ...RequestFails.parameters, a11y: { test: "todo" } },
};

/** Cancelling after a refused request drops the error, so the reopened dialog starts clean. */
export const ClearsErrorOnCancel: Story = {
    ...RequestFails,
    play: async (context) => {
        const dialog = await openRequestDialog(context);
        await seeRequestFail(context, dialog);
        await cancelDialog(context, dialog);
        const reopened = await openRequestDialog(context);
        await context.step("See the question again with no error", async () => {
            await seeQuestion(reopened, "2 missing tools");
            await expect(within(reopened).queryByRole("alert")).not.toBeInTheDocument();
        });
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { ...RequestFails.parameters, a11y: { test: "todo" } },
};

/** The admins turned the request form off: no button. */
export const RequestFormOff: Story = {
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({
                    ...REQUESTS_ENABLED,
                    enable_tool_installation_request_form: false,
                }),
            },
        },
    },
};

/** Without the notification system a request can't reach the admins: no button. */
export const NotificationSystemOff: Story = {
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ ...REQUESTS_ENABLED, enable_notification_system: false }),
            },
        },
    },
};

/** Anonymous visitors can't send requests: no button. */
export const AnonymousVisitor: Story = {
    parameters: viewedBy(getFakeAnonymousUser()),
};
