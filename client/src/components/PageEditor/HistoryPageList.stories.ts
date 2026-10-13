import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { expect, fn, within } from "storybook/test";
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

type Canvas = ReturnType<typeof within>;

/** Waits for the history's name in the breadcrumb, which loads with its owner, so ownership is settled. */
async function findHistoryHeading(canvas: Canvas) {
    const heading = await canvas.findByRole(
        "heading",
        { name: (name: string) => name.includes(NOTEBOOK_HISTORY.name) },
        { timeout: 5000 },
    );
    // The only history in the store counts as current.
    expect(heading).toHaveTextContent(/^Histories \/ Paired-end RNA-seq current \/ Galaxy Notebooks$/);
    return heading;
}

/** The user's own history, with no notebooks yet. */
export const NoNotebooks: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Name the history in the breadcrumb and offer a new notebook", async () => {
            expect(await findHistoryHeading(canvas)).toBeVisible();
            expect(canvas.getByRole("button", { name: /^New Notebook$/ })).toBeVisible();
        });
        await step("Explain there are no notebooks yet and how to start one", async () => {
            expect(canvas.getByText("No notebooks yet", { exact: true })).toBeVisible();
            expect(
                canvas.getByText(
                    "Create a notebook to document your analysis with rich markdown, embedded datasets, and visualizations.",
                    { exact: true },
                ),
            ).toBeVisible();
        });
        await step("Don't warn about ownership on the user's own history", async () => {
            expect(canvas.queryByRole("status")).toBeNull();
            expect(canvas.queryByRole("alert")).toBeNull();
            expect(canvas.queryByText(/You do not own this history/)).toBeNull();
        });
    },
};

/** The user's own history with two notebooks, one still untitled. */
export const WithNotebooks: Story = {
    args: { pages: [FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED] },
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("List each notebook by title, naming the untitled one", async () => {
            const analysis = await canvas.findByRole("heading", { name: "My Analysis" });
            const untitled = canvas.getByRole("heading", { name: "Untitled Notebook" });
            expect(analysis).toBeVisible();
            expect(untitled).toBeVisible();
            // In the order given, after the breadcrumb.
            expect(canvas.getAllByRole("heading").slice(1)).toEqual([analysis, untitled]);
        });
        await step("Show no empty-state message beside them", async () => {
            expect(canvas.queryByText("No notebooks yet")).toBeNull();
            expect(canvas.queryByText(/Create a notebook to document your analysis/)).toBeNull();
        });
    },
};

/** Another user's history, where only the viewer's own notebooks would be listed: none yet. */
export const OtherUsersHistory: Story = {
    parameters: { msw: { handlers: { history: notebookHistory(OTHER_USERS_NOTEBOOK_HISTORY) } } },
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Warn that only the viewer's own notebooks are listed", async () => {
            const alert = await canvas.findByRole("status", {}, { timeout: 5000 });
            expect(alert).toBeVisible();
            expect(alert).toHaveTextContent(
                /^You do not own this history so only Galaxy Notebooks that you created against this history are shown\.$/,
            );
        });
    },
};

/** An invocation's edited reports, for a run in another user's history: no reports yet. */
export const OtherUsersInvocation: Story = {
    args: { invocationId: "inv-1" },
    parameters: { msw: { handlers: { history: notebookHistory(OTHER_USERS_NOTEBOOK_HISTORY) } } },
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Warn that only the viewer's own reports on the invocation's history are listed", async () => {
            const alert = await canvas.findByRole("status", {}, { timeout: 5000 });
            expect(alert).toBeVisible();
            expect(alert).toHaveTextContent(
                /^You do not own this history \(associated with the invocation\) so only Invocation Reports that you created against this history are shown\.$/,
            );
        });
    },
};

/** The user's own history as their history list loaded it, before anything asked for its owner. */
export const ListedHistory: Story = {
    decorators: [withListedHistory(getFakeHistorySummary({ id: NOTEBOOK_HISTORY.id, name: NOTEBOOK_HISTORY.name }))],
};
