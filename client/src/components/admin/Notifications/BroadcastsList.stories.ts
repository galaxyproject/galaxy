import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { http } from "@/api/client/__mocks__/http";
import { broadcast, type BroadcastScenario, DAY, HOUR } from "@/components/Notifications/Broadcasts/test_fixtures";

import BroadcastsList from "./BroadcastsList.vue";

const ONE_OF_EACH: BroadcastScenario[] = [
    {
        id: "a7c1ee54b2d8f390",
        variant: "info",
        subject: "Galaxy 26.1 is live",
        message: "See the **release notes** for what's new.",
        publishedIn: -2 * HOUR,
        expiresIn: 5 * DAY,
    },
    {
        id: "5f2b9d0c3e6a1847",
        variant: "warning",
        subject: "Maintenance on Saturday",
        message: "Jobs queued during the window will start once it ends.",
        publishedIn: 2 * DAY,
        expiresIn: 3 * DAY,
    },
    {
        id: "c39e8a7d1b40f256",
        variant: "urgent",
        subject: "Storage outage resolved",
        message: "Uploads work again.",
        publishedIn: -3 * DAY,
        expiresIn: -1 * DAY,
    },
];

/** Answers the admin's request for every broadcast, timed from the moment of the request. */
function allBroadcasts(scenarios: BroadcastScenario[]) {
    return http.get("/api/notifications/broadcast", ({ response }) => {
        const now = Date.now();
        return response(200).json(scenarios.map((scenario) => broadcast(now, scenario)));
    });
}

const meta = {
    title: "admin/Notifications/BroadcastsList",
    component: BroadcastsList,
    parameters: { msw: { handlers: { broadcasts: allBroadcasts(ONE_OF_EACH) } } },
} satisfies Meta<typeof BroadcastsList>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An active, a scheduled and an expired broadcast, newest first. */
export const OneOfEach: Story = {};

/** No broadcasts yet, so the list says how to create one. */
export const NoBroadcasts: Story = {
    parameters: { msw: { handlers: { broadcasts: allBroadcasts([]) } } },
};
