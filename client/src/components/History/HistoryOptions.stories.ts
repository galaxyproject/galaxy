import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser, getFakeHistorySummaryExtended } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { withToasts } from "@tests/test-data/toasts";

import { ANALYSIS_HISTORY, HISTORY_VIEWER, historyOperationsStory } from "./test_fixtures";

import HistoryOptions from "./HistoryOptions.vue";

const deletedHistory = getFakeHistorySummaryExtended({ ...ANALYSIS_HISTORY, deleted: true });
const anonymousHistory = getFakeHistorySummaryExtended({ ...ANALYSIS_HISTORY, user_id: null });
const anonymousOperations = historyOperationsStory(anonymousHistory);
const sharedHistory = getFakeHistorySummaryExtended({ ...ANALYSIS_HISTORY, user_id: "d0ae172bc345689f" });

const meta = {
    title: "History/HistoryOptions",
    component: HistoryOptions,
    decorators: [withCurrentUser(() => HISTORY_VIEWER), withToasts],
    args: { history: ANALYSIS_HISTORY },
} satisfies Meta<typeof HistoryOptions>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An owned history offers copy, delete, export and sharing operations. */
export const OwnedHistory: Story = { ...historyOperationsStory() };

/** A deleted history can be permanently removed; its purge option is already selected. */
export const DeletedHistory: Story = {
    args: { history: deletedHistory },
    ...historyOperationsStory(deletedHistory),
};

/** A session history keeps basic operations available and explains account-only options. */
export const AnonymousHistory: Story = {
    args: { history: anonymousHistory },
    ...anonymousOperations,
    parameters: {
        ...anonymousOperations.parameters,
        ...viewedBy(getFakeAnonymousUser()),
    },
};

/** Another user's accessible history offers copy and read-only views rather than owner actions. */
export const UnownedHistory: Story = {
    args: { history: sharedHistory },
    ...historyOperationsStory(sharedHistory),
};
