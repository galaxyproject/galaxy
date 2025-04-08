<script setup lang="ts">
import { faShareAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { hasImportable } from "@/api/histories";
import { getFullAppUrl } from "@/app/utils";
import { Toast } from "@/composables/toast";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { useHistoryStore } from "@/stores/historyStore";
import { copy } from "@/utils/clipboard";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "../LoadingSpan.vue";

const CLIPBOARD_MSG = "The link to the invocation has been copied to your clipboard.";

const props = defineProps<{
    invocationId: string;
    workflowId: string;
    historyId: string;
}>();

const modalToggle = ref(false);

// Workflow and History refs
const { workflow, loading, error, owned } = useWorkflowInstance(props.workflowId);
const historyStore = useHistoryStore();
const history = computed(() => historyStore.getHistoryById(props.historyId));

/** The link to the invocation. */
const invocationLink = computed(() => getFullAppUrl(`workflows/invocations/${props.invocationId}`));

/** If the history is already shareable.
 * (i.e. It has the `importable` property, and it is set to `true`)
 */
const historyAlreadyShareable = computed(() => {
    // Note: We will mostly have a summarized history object without the importable property
    //       and in that case we still attempt to make it shareable.
    return Boolean(history.value && hasImportable(history.value) && history.value.importable);
});

/** If the workflow is already shareable. */
const workflowAlreadyShareable = computed(() => Boolean(workflow.value && workflow.value.importable));

/** If both the workflow and history are already shareable. */
const historyAndWorkflowAlreadyShareable = computed(
    () => historyAlreadyShareable.value && workflowAlreadyShareable.value
);

async function makeInvocationShareable() {
    if (!workflow.value) {
        return;
    }

    let errorMessage = "";
    let shared = false;
    if (!workflowAlreadyShareable.value) {
        const { error: workflowShareError } = await GalaxyApi().PUT("/api/workflows/{workflow_id}/enable_link_access", {
            params: { path: { workflow_id: workflow.value.id } },
        });
        shared = true;
        if (workflowShareError) {
            errorMessage = errorMessageAsString(workflowShareError);
        }
    }
    if (!historyAlreadyShareable.value) {
        const { error: historyShareError } = await GalaxyApi().PUT("/api/histories/{history_id}/enable_link_access", {
            params: { path: { history_id: props.historyId } },
        });
        shared = true;
        if (historyShareError) {
            errorMessage += errorMessageAsString(historyShareError);
        }
    }

    if (errorMessage) {
        Toast.error(errorMessage, "Failed to make workflow and history shareable.");
        return;
    } else if (shared) {
        Toast.success("Workflow and history are now shareable.");
    }

    copy(invocationLink.value, CLIPBOARD_MSG);
}

function shareInvocationButtonClicked() {
    if (historyAndWorkflowAlreadyShareable.value) {
        copy(invocationLink.value, CLIPBOARD_MSG);
    } else {
        modalToggle.value = true;
    }
}
</script>

<template>
    <div v-if="owned">
        <BButton
            v-b-tooltip.noninteractive.hover
            title="Share Invocation"
            size="sm"
            class="text-decoration-none"
            data-description="share invocation icon button"
            variant="link"
            :disabled="!workflow"
            @click="shareInvocationButtonClicked">
            <FontAwesomeIcon :icon="faShareAlt" fixed-width />
        </BButton>

        <BModal
            v-model="modalToggle"
            title="Share Workflow Invocation"
            title-tag="h2"
            ok-title="Share"
            data-description="share invocation modal"
            @ok="makeInvocationShareable">
            <BAlert v-if="error" variant="danger" show>
                {{ error }}
            </BAlert>

            <LoadingSpan v-else-if="loading" message="Loading details for invocation" />

            <div v-else-if="workflow">
                <p v-localize>
                    To share this invocation, you need to make sure that the workflow
                    <strong>"{{ workflow.name }}"</strong>
                    and history
                    <strong>"{{ historyStore.getHistoryNameById(props.historyId) }}"</strong>
                    are accessible via link.
                </p>
                <p v-localize>
                    You can do this by clicking the <i>"Share"</i>
                    button below. This will
                    <strong>make the workflow and history shareable</strong>
                    and generate a link that you can share with others, allowing them to view the invocation.
                </p>
            </div>
        </BModal>
    </div>
</template>
