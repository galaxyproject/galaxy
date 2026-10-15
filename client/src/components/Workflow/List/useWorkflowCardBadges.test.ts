import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { WorkflowSummary } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";

import { useWorkflowCardBadges } from "./useWorkflowCardBadges";

vi.mock("vue-router/composables", () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

const { server, http } = useServerMock();

const USERNAME = "fake_username";

function makeWorkflow(owner: string, extra: Partial<WorkflowSummary> = {}): WorkflowSummary {
    return { id: `workflow-${owner}`, name: "wf", owner, ...extra } as WorkflowSummary;
}

function renderBadges(workflow: WorkflowSummary, { hideRuns = false, publishedView = false } = {}) {
    const { workflowCardBadges } = useWorkflowCardBadges(ref(workflow), publishedView, true, hideRuns, vi.fn());
    // read every badge label, as GCard does when rendering
    workflowCardBadges.value.forEach((b) => b.label);
    return workflowCardBadges;
}

describe("useWorkflowCardBadges", () => {
    let countRequests: string[];

    beforeEach(() => {
        setActivePinia(createPinia());
        countRequests = [];
        server.use(
            http.get("/api/workflows/{workflow_id}/counts", ({ params, response }) => {
                countRequests.push(params.workflow_id);
                return response(200).json({ scheduled: 2 });
            }),
        );
        useUserStore().currentUser = getFakeRegisteredUser({ username: USERNAME });
    });

    it("fetches invocation count for an owned workflow", async () => {
        const badges = renderBadges(makeWorkflow(USERNAME));
        await flushPromises();
        expect(countRequests).toEqual([`workflow-${USERNAME}`]);
        const countBadge = badges.value.find((b) => b.id === "invocations-count");
        expect(countBadge?.visible).toBe(true);
        expect(countBadge?.label).toBe("workflow runs: 2");
    });
});
