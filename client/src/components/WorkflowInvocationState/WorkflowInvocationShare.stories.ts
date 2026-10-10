import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";
import { computed, h } from "vue";

import { http } from "@/api/client/__mocks__/http";
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
 * invocation's workflow and history. Renders the story once both have loaded.
 */
const withInvocationPage: Decorator = (story, { args }) => ({
    setup() {
        useUserStore().setCurrentUser(SIGNED_IN_USER);
        const workflowStore = useWorkflowStore();
        const historyStore = useHistoryStore();
        workflowStore.fetchWorkflowForInstanceIdCached(args.workflowId as string);
        historyStore.loadHistoryById(args.historyId as string);
        const loaded = computed(() =>
            Boolean(
                workflowStore.getStoredWorkflowByInstanceId(args.workflowId as string) &&
                    historyStore.getHistoryById(args.historyId as string, false),
            ),
        );
        return () => (loaded.value ? h(story()) : null);
    },
});

const meta = {
    title: "WorkflowInvocationState/WorkflowInvocationShare",
    component: WorkflowInvocationShare,
    decorators: [withInvocationPage],
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

/** The user's own workflow and history, not shared yet: sharing asks first, in a dialog. */
export const NotYetShareable: Story = {};

/** Both are already accessible via link, so sharing only copies the invocation's link. */
export const AlreadyShareable: Story = {
    parameters: {
        msw: { handlers: { workflow: workflow({ importable: true }), history: history({ importable: true }) } },
    },
};

/** Someone else's workflow ran in the user's history: there's no share button. */
export const SomeoneElsesWorkflow: Story = {
    parameters: { msw: { handlers: { workflow: workflow({ owner: OTHER_USER.username }) } } },
};

/** The user's workflow ran in someone else's history: there's no share button. */
export const SomeoneElsesHistory: Story = {
    parameters: { msw: { handlers: { history: history({ owner: OTHER_USER.id }) } } },
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
};
