import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { h } from "vue";

import { broadcast, broadcastsState, DAY, withBroadcastsState } from "./test_fixtures";

import BroadcastsOverlay from "./BroadcastsOverlay.vue";

const meta = {
    title: "Notifications/BroadcastsOverlay",
    component: BroadcastsOverlay,
    decorators: [withBroadcastsState],
    render: () => () => h("div", [h("h2", "Galaxy workspace"), h(BroadcastsOverlay)]),
} satisfies Meta<typeof BroadcastsOverlay>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Browse current maintenance notices, or dismiss them one at a time. */
export const NoticesQueue: Story = {
    parameters: broadcastsState(() => {
        const now = Date.now();
        return [
            broadcast(
                now,
                {
                    id: "maintenance",
                    variant: "info",
                    subject: "Planned maintenance",
                    message: "Galaxy will be unavailable briefly on Saturday for maintenance.",
                    publishedIn: -DAY,
                    expiresIn: 7 * DAY,
                },
                true,
            ),
            broadcast(
                now,
                {
                    id: "training",
                    variant: "info",
                    subject: "Training sessions",
                    message: "Explore the upcoming Galaxy training sessions.",
                    publishedIn: -DAY,
                    expiresIn: 7 * DAY,
                },
                true,
            ),
        ];
    }),
};

/** Urgent notices appear before warnings and informational notices. */
export const PriorityNotices: Story = {
    parameters: broadcastsState(() => {
        const now = Date.now();
        return [
            broadcast(
                now,
                {
                    id: "capacity",
                    variant: "warning",
                    subject: "Storage capacity",
                    message: "Storage is nearly full. Review unneeded datasets.",
                    publishedIn: -DAY,
                    expiresIn: 7 * DAY,
                },
                true,
            ),
            broadcast(
                now,
                {
                    id: "training",
                    variant: "info",
                    subject: "Training sessions",
                    message: "New training sessions are available.",
                    publishedIn: -DAY,
                    expiresIn: 7 * DAY,
                },
                true,
            ),
            broadcast(
                now,
                {
                    id: "outage",
                    variant: "urgent",
                    subject: "Service interruption",
                    message: "Some jobs are paused while a service interruption is resolved.",
                    publishedIn: -DAY,
                    expiresIn: 7 * DAY,
                },
                true,
            ),
        ];
    }),
};

/** Broadcast messages support documentation links rendered safely in a new tab. */
export const DocumentationNotice: Story = {
    parameters: broadcastsState(() => [
        broadcast(
            Date.now(),
            {
                id: "documentation",
                variant: "info",
                subject: "Galaxy documentation",
                message: "Read the [Galaxy documentation](https://docs.galaxyproject.org/).",
                publishedIn: -DAY,
                expiresIn: 7 * DAY,
            },
            true,
        ),
    ]),
};

/** The workspace has no visible notice when no broadcasts are active. */
export const NoActiveNotices: Story = { parameters: broadcastsState(() => []) };
