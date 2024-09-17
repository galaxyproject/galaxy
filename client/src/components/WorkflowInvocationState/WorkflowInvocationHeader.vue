<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faArrowLeft, faEdit, faHdd, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import localize from "@/utils/localization";

import Heading from "../Common/Heading.vue";
import SwitchToHistoryLink from "../History/SwitchToHistoryLink.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationsCount from "../Workflow/WorkflowInvocationsCount.vue";
import WorkflowRunButton from "../Workflow/WorkflowRunButton.vue";

interface Props {
    invocation: WorkflowInvocationElementView;
    fromPanel?: boolean;
}

const props = defineProps<Props>();

const { workflow } = useWorkflowInstance(props.invocation.workflow_id);

function getWorkflowName(): string {
    return workflow.value?.name || "...";
}
</script>

<template>
    <div>
        <div class="d-flex flex-gapx-1">
            <Heading h1 separator inline truncate size="xl" class="flex-grow-1">
                Invoked Workflow: "{{ getWorkflowName() }}"
            </Heading>

            <div v-if="!props.fromPanel">
                <BButton
                    v-b-tooltip.hover.noninteractive
                    :title="localize('Return to Invocations List')"
                    class="text-nowrap"
                    size="sm"
                    variant="outline-primary"
                    to="/workflows/invocations">
                    <FontAwesomeIcon :icon="faArrowLeft" class="mr-1" />
                    <span v-localize>Invocations List</span>
                </BButton>
            </div>
        </div>
        <div class="py-2 pl-3 d-flex justify-content-between align-items-center">
            <div>
                <i>
                    <FontAwesomeIcon :icon="faClock" class="mr-1" />invoked
                    <UtcDate :date="props.invocation.update_time" mode="elapsed" />
                </i>
                <span class="d-flex flex-gapx-1 align-items-center">
                    <FontAwesomeIcon :icon="faHdd" />History:
                    <SwitchToHistoryLink :history-id="props.invocation.history_id" />
                </span>
            </div>
            <div v-if="workflow" class="d-flex flex-gapx-1 align-items-center">
                <div class="d-flex flex-column align-items-end mr-2">
                    <span v-if="workflow.version !== undefined" class="mb-1">
                        <FontAwesomeIcon :icon="faSitemap" />
                        Workflow Version: {{ workflow.version + 1 }}
                    </span>
                    <WorkflowInvocationsCount class="float-right" :workflow="workflow" />
                </div>
                <BButtonGroup vertical>
                    <BButton
                        v-b-tooltip.hover.noninteractive.html
                        :title="
                            !workflow.deleted
                                ? `<b>Edit</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        size="sm"
                        variant="secondary"
                        :disabled="workflow.deleted"
                        :to="`/workflows/edit?id=${workflow.id}&version=${workflow.version}`">
                        <FontAwesomeIcon :icon="faEdit" />
                        <span v-localize>Edit</span>
                    </BButton>
                    <WorkflowRunButton
                        :id="workflow.id || ''"
                        :title="
                            !workflow.deleted
                                ? `<b>Rerun</b><br>${getWorkflowName()}`
                                : 'This workflow has been deleted.'
                        "
                        :disabled="workflow.deleted"
                        full
                        :version="workflow.version" />
                </BButtonGroup>
            </div>
        </div>
    </div>
</template>
