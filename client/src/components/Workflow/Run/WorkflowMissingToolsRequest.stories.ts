import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";

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

/** The workflow uses two tools this Galaxy hasn't installed; the user can ask the admins for them. */
export const MissingTools: Story = {};

/** Just one tool is missing. */
export const OneMissingTool: Story = {
    args: { missingToolIds: ["toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"] },
};

/** More tools are missing than one request can carry; the dialog says only the first 50 are sent. */
export const OverRequestLimit: Story = {
    args: { missingToolIds: Array.from({ length: 60 }, (_, i) => `tool-${i}`) },
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
