import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { fn } from "storybook/test";
import { h } from "vue";

import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import {
    FAKE_PAGE_SUMMARY,
    FAKE_PAGE_UNTITLED,
    NOTEBOOK_HISTORY,
    notebookHistory,
    OTHER_USERS_NOTEBOOK_HISTORY,
} from "./testData";

import HistoryPageList from "./HistoryPageList.vue";

/** Stores `history` as the user's history list loads it, which doesn't say who owns it. */
function withListedHistory(history: HistorySummary): Decorator {
    return (story) => ({
        setup() {
            useHistoryStore().setHistories([history]);
        },
        render: () => h(story()),
    });
}

/** The notebooks a user has written against one history, as the history's Notebooks page lists them. */
const meta = {
    title: "PageEditor/HistoryPageList",
    component: HistoryPageList,
    decorators: [withCurrentUser(() => getFakeRegisteredUser({ username: FAKE_PAGE_SUMMARY.username }))],
    args: {
        historyId: NOTEBOOK_HISTORY.id,
        pages: [],
        onCreate: fn(),
        onEdit: fn(),
        onView: fn(),
        "onView-runtime-report": fn(),
    },
    parameters: {
        msw: { handlers: { history: notebookHistory(NOTEBOOK_HISTORY) } },
    },
} satisfies Meta<typeof HistoryPageList>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The user's own history, with no notebooks yet. */
export const NoNotebooks: Story = {};

/** The user's own history with two notebooks, one still untitled. */
export const WithNotebooks: Story = {
    args: { pages: [FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED] },
};

/** Another user's history, where only the viewer's own notebooks would be listed: none yet. */
export const OtherUsersHistory: Story = {
    parameters: { msw: { handlers: { history: notebookHistory(OTHER_USERS_NOTEBOOK_HISTORY) } } },
};

/** An invocation's edited reports, for a run in another user's history: no reports yet. */
export const OtherUsersInvocation: Story = {
    args: { invocationId: "inv-1" },
    parameters: { msw: { handlers: { history: notebookHistory(OTHER_USERS_NOTEBOOK_HISTORY) } } },
};

/** The user's own history as their history list loaded it, before anything asked for its owner. */
export const ListedHistory: Story = {
    decorators: [withListedHistory(getFakeHistorySummary({ id: NOTEBOOK_HISTORY.id, name: NOTEBOOK_HISTORY.name }))],
};
