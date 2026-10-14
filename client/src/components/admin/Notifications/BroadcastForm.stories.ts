import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withToasts } from "@tests/test-data/toasts";

import {
    broadcastFormHandlers,
    broadcastsState,
    PUBLISHED_BROADCAST_ID,
    SCHEDULED_BROADCAST_ID,
    withBroadcastsState,
} from "@/components/Notifications/Broadcasts/test_fixtures";

import BroadcastForm from "./BroadcastForm.vue";

const meta = {
    title: "Admin/Notifications/BroadcastForm",
    component: BroadcastForm,
    decorators: [withToasts, withBroadcastsState],
    parameters: { ...broadcastsState(() => []), msw: { handlers: broadcastFormHandlers() } },
} satisfies Meta<typeof BroadcastForm>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Write a notice, set its publication dates, and preview it before saving. */
export const NewBroadcast: Story = {};

/** Edit a notice scheduled for tomorrow, including its documentation action link. */
export const ScheduledBroadcast: Story = { args: { id: SCHEDULED_BROADCAST_ID } };

/** Editing an already published notice warns that readers can see the current text. */
export const PublishedBroadcast: Story = { args: { id: PUBLISHED_BROADCAST_ID } };
