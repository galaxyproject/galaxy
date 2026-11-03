import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { INVOCATION, INVOKED_WORKFLOW } from "@/components/WorkflowInvocationState/test_fixtures";

export const SIGNED_IN_USER = getFakeRegisteredUser({ username: "alice" });

/** The invoked workflow as the signed-in user's own. */
export const OWN_WORKFLOW: StoredWorkflowDetailed = {
    ...INVOKED_WORKFLOW,
    owner: SIGNED_IN_USER.username,
    annotation: "Aligns paired-end reads to hg38 and counts reads per gene.",
};

/** The invoked workflow as another user's published one. */
export const PUBLISHED_WORKFLOW: StoredWorkflowDetailed = { ...INVOKED_WORKFLOW, owner: "bob", published: true };

/** How often the signed-in user has run their workflow, by invocation state. */
export const OWN_WORKFLOW_RUNS = { scheduled: 12 };

/** The history the invocation ran in, the user's current one. */
export const INVOCATION_HISTORY = getFakeHistorySummary({
    id: INVOCATION.history_id,
    name: "RNA-seq run",
    url: `/api/histories/${INVOCATION.history_id}`,
});
