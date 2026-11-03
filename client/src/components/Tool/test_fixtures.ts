import type { Decorator } from "@storybook/vue3-vite";
import { getActivePinia } from "pinia";
import { h, onBeforeUnmount } from "vue";

import type { JobBaseModel, ResponseVal } from "@/api/jobs";
import { CURRENT_HISTORY } from "@/components/SelectionField/test_fixtures";
import { useJobStore } from "@/stores/jobStore";

export const QUEUED_CAT_JOB = {
    id: "4cf178ac763ea2f1",
    tool_id: "cat1",
    model_class: "Job",
    history_id: CURRENT_HISTORY.id,
    state: "new",
    create_time: "2026-10-01T12:00:00",
    update_time: "2026-10-01T12:00:00",
} satisfies JobBaseModel;

// tools/filters/catWrapper.xml takes input1 plus repeated queries.input2, producing out_file1.
export const CAT_SUBMISSION: ResponseVal = {
    jobDef: {
        tool_id: "cat1",
        tool_version: "1.0.0",
        history_id: CURRENT_HISTORY.id,
        inputs: {
            input1: { id: "f2db41e1fa331b3e", src: "hda" },
            queries: [{ input2: { id: "afec4c9cbdd0bf88", src: "hda" } }],
        },
        send_email_notification: false,
        strict: true,
    },
    // The submission store uses this typed projection of the tools API response.
    jobResponse: {
        produces_entry_points: false,
        jobs: [QUEUED_CAT_JOB],
        outputs: [
            {
                id: "d8f6e2b17c4a9035",
                history_content_type: "dataset",
                hid: 3,
                name: "Concatenate multiple datasets or collections on data 1 and data 2",
            },
        ],
        output_collections: [],
    },
};

/** The tool form has saved its successful submission before navigating to this page. */
export function withToolSubmission(submission: ResponseVal = CAT_SUBMISSION): Decorator {
    return (story) => ({
        setup() {
            const pinia = getActivePinia();
            if (!pinia) {
                throw new Error("Tool submission stories need Pinia");
            }
            const existed = pinia._s.has("jobStore");
            const previousState = pinia.state.value.jobStore;
            const store = useJobStore(pinia);
            const previousResponse = store.latestResponse;
            store.latestResponse = structuredClone(submission);
            onBeforeUnmount(() => {
                store.latestResponse = previousResponse;
                if (!existed) {
                    store.$dispose();
                    if (previousState === undefined) {
                        delete pinia.state.value[store.$id];
                    } else {
                        pinia.state.value[store.$id] = previousState;
                    }
                }
            });
            return () => h(story());
        },
    });
}
