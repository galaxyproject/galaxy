import { GToast } from "@galaxyproject/galaxy-ui";
import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";
import { expect, fn, waitFor, within } from "storybook/test";
import { computed, h, onUnmounted } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import WorkflowInvocationShare from "./WorkflowInvocationShare.vue";

const SIGNED_IN_USER = getFakeRegisteredUser({ username: "alice" });
const OTHER_USER = getFakeRegisteredUser({ id: "b8d4e2f6a1c39075", username: "bob" });
const WORKFLOW_ID = "f2db41e1fa331b3e";
const HISTORY_ID = "a7e3b9c1d5f20864";
const WORKFLOW_NAME = "RNA-seq alignment";
const HISTORY_NAME = "RNA-seq run";

interface ItemAccess {
    /** Who owns it; the signed-in user if not given. */
    owner?: string;
    /** Whether it's already accessible via link. */
    importable?: boolean;
}

/** Answers the invocation's workflow, owned by `owner` (a username). */
function workflow({ owner = SIGNED_IN_USER.username, importable = false }: ItemAccess = {}) {
    return http.get("/api/workflows/{workflow_id}", ({ response }) =>
        response.untyped(
            HttpResponse.json(getFakeWorkflowSummary({ id: WORKFLOW_ID, name: WORKFLOW_NAME, owner, importable })),
        ),
    );
}

/** Answers the invocation's history, owned by `owner` (a user id). */
function history({ owner = SIGNED_IN_USER.id, importable = false }: ItemAccess = {}) {
    return http.get("/api/histories/{history_id}", ({ response }) =>
        response.untyped(
            HttpResponse.json({
                ...getFakeHistorySummaryExtended({ id: HISTORY_ID, name: HISTORY_NAME, user_id: owner }),
                importable,
            }),
        ),
    );
}

/** Galaxy's answer to making an item accessible via link. */
function linkAccessEnabled(id: string, title: string) {
    return { id, title, importable: true, published: false, users_shared_with: [] };
}

/**
 * The share button sits on the invocation page: a user is signed in, and the page has loaded the
 * invocation's workflow and history. Renders the story once both have loaded, under the page's
 * heading naming the workflow, which plays wait for before checking the button isn't there.
 */
const withInvocationPage: Decorator = (story, { args }) => ({
    setup() {
        useUserStore().setCurrentUser(SIGNED_IN_USER);
        const workflowStore = useWorkflowStore();
        const historyStore = useHistoryStore();
        workflowStore.fetchWorkflowForInstanceIdCached(args.workflowId as string);
        historyStore.loadHistoryById(args.historyId as string);
        const workflow = computed(() => workflowStore.getStoredWorkflowByInstanceId(args.workflowId as string));
        const loaded = computed(() =>
            Boolean(workflow.value && historyStore.getHistoryById(args.historyId as string, false)),
        );
        return () =>
            loaded.value ? h("div", [h("h2", `Invoked Workflow: ${workflow.value?.name}`), h(story())]) : null;
    },
});

/** What the page copied to the clipboard. */
const copiedToClipboard = fn(async (_text: string) => {}).mockName("navigator.clipboard.writeText");

/**
 * The app shell's toast stack, which shows what sharing did, and a clipboard that records what
 * was copied: the browser refuses clipboard writes from a play's scripted clicks.
 */
const withToastsAndClipboard: Decorator = (story) => ({
    setup() {
        useToast().clearToasts();
        copiedToClipboard.mockClear();
        const clipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");
        Object.defineProperty(navigator, "clipboard", {
            configurable: true,
            value: { writeText: copiedToClipboard },
        });
        onUnmounted(() => {
            if (clipboard) {
                Object.defineProperty(navigator, "clipboard", clipboard);
            } else {
                delete (navigator as { clipboard?: Clipboard }).clipboard;
            }
        });
    },
    render: () => h("div", [h(story()), h(GToast)]),
});

const meta = {
    title: "WorkflowInvocationState/WorkflowInvocationShare",
    component: WorkflowInvocationShare,
    decorators: [withInvocationPage, withToastsAndClipboard],
    args: { invocationId: "c94e7b1205a34d8e", workflowId: WORKFLOW_ID, historyId: HISTORY_ID },
    parameters: {
        msw: {
            handlers: {
                workflow: workflow(),
                history: history(),
                shareWorkflow: http.put("/api/workflows/{workflow_id}/enable_link_access", ({ response }) =>
                    response(200).json(linkAccessEnabled(WORKFLOW_ID, WORKFLOW_NAME)),
                ),
                shareHistory: http.put("/api/histories/{history_id}/enable_link_access", ({ response }) =>
                    response(200).json(linkAccessEnabled(HISTORY_ID, HISTORY_NAME)),
                ),
            },
        },
    },
} satisfies Meta<typeof WorkflowInvocationShare>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const INVOCATION_LINK = /^https?:\/\/[^/]+\/workflows\/invocations\/c94e7b1205a34d8e$/;

/** The page loads its workflow and history first, which can take a while when every story runs. */
const PAGE_LOAD = { timeout: 5000 };

/** Clicks the share button once the page has loaded the invocation's workflow and history. */
async function clickShare({ canvas, step, userEvent }: PlayContext) {
    await step("Click Share Invocation", async () => {
        // Find the button first: until the page has loaded, there's no dialog to see either way.
        const button = await canvas.findByRole("button", { name: "Share Invocation" }, PAGE_LOAD);
        await expect(canvas.queryByRole("dialog")).not.toBeInTheDocument();
        await userEvent.click(button);
    });
}

/** Checks the toasts on screen, oldest first, by their whole text: title then message. */
async function seeToasts({ canvas }: PlayContext, toasts: [title: string, message: string][]) {
    await waitFor(() => expect(canvas.getAllByRole("alert")).toHaveLength(toasts.length));
    const shown = canvas.getAllByRole("alert");
    for (const [index, [title, message]] of toasts.entries()) {
        await expect(shown[index]).toHaveTextContent(new RegExp(`^${title} ${message.replace(/\./g, "\\.")}$`));
    }
}

/** Once the page shows the invocation, checks there's no way to share it. */
async function seeNoShareButton({ canvas, canvasElement, step }: PlayContext) {
    await step("See the invocation's page with no share button", async () => {
        await expect(
            await canvas.findByRole("heading", { name: "Invoked Workflow: RNA-seq alignment" }, PAGE_LOAD),
        ).toBeVisible();
        await expect(canvas.queryByRole("button", { name: "Share Invocation" })).not.toBeInTheDocument();
        // Not even a closed share dialog: role queries can't see one, so look for the element.
        await expect(canvasElement.querySelector("dialog")).toBeNull();
    });
}

/** Checks the invocation's link was copied, once. */
async function seeLinkCopied() {
    await expect(copiedToClipboard).toHaveBeenCalledTimes(1);
    await expect(copiedToClipboard).toHaveBeenCalledWith(expect.stringMatching(INVOCATION_LINK));
}

/** The user's own workflow and history, not shared yet: sharing asks first, in a dialog. */
export const NotYetShareable: Story = {};

/** The dialog names the workflow and history that sharing will make accessible via link. */
export const AsksBeforeSharing: Story = {
    play: async (context) => {
        await clickShare(context);
        await context.step("See the dialog name the workflow and history", async () => {
            const dialog = await context.canvas.findByRole("dialog");
            await expect(within(dialog).getByRole("heading", { name: "Share Workflow Invocation" })).toBeVisible();
            await expect(within(dialog).getAllByRole("paragraph")[0]).toHaveTextContent(
                /^To share this invocation, you need to make sure that the workflow "RNA-seq alignment" and history "RNA-seq run" are accessible via link\.$/,
            );
        });
    },

    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Confirming shares both, closes the dialog and copies the invocation's link. */
export const SharesAndCopiesLink: Story = {
    play: async (context) => {
        await clickShare(context);
        await context.step("Share from the dialog", async () => {
            const dialog = await context.canvas.findByRole("dialog");
            await expect(copiedToClipboard).not.toHaveBeenCalled();
            await context.userEvent.click(within(dialog).getByRole("button", { name: "Share" }));
        });
        await context.step("See both shared and the link copied", async () => {
            await seeToasts(context, [
                ["Success", "Workflow and history are now shareable."],
                ["Info", "The link to the invocation has been copied to your clipboard."],
            ]);
            await expect(context.canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await seeLinkCopied();
        });
    },
};

/** Both are already accessible via link, so sharing only copies the invocation's link. */
export const AlreadyShareable: Story = {
    parameters: {
        msw: { handlers: { workflow: workflow({ importable: true }), history: history({ importable: true }) } },
    },
};

/** With both already shareable, the share button copies the link without asking. */
export const CopiesLinkWithoutAsking: Story = {
    ...AlreadyShareable,
    play: async (context) => {
        await clickShare(context);
        await context.step("See the link copied, with no dialog", async () => {
            await seeToasts(context, [["Info", "The link to the invocation has been copied to your clipboard."]]);
            await expect(context.canvas.queryByRole("dialog")).not.toBeInTheDocument();
            await seeLinkCopied();
        });
    },
};

/** Someone else's workflow ran in the user's history: there's no share button. */
export const SomeoneElsesWorkflow: Story = {
    parameters: { msw: { handlers: { workflow: workflow({ owner: OTHER_USER.username }) } } },
    play: seeNoShareButton,
};

/** The user's workflow ran in someone else's history: there's no share button. */
export const SomeoneElsesHistory: Story = {
    parameters: { msw: { handlers: { history: history({ owner: OTHER_USER.id }) } } },
    play: seeNoShareButton,
};

/** Someone else's invocation: there's no share button. */
export const SomeoneElsesInvocation: Story = {
    parameters: {
        msw: {
            handlers: {
                workflow: workflow({ owner: OTHER_USER.username }),
                history: history({ owner: OTHER_USER.id }),
            },
        },
    },
    play: seeNoShareButton,
};
