<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faDownload, faEdit, faPlay, faSpinner, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";

library.add(faBuilding, faDownload, faEdit, faPlay, faSpinner, faUser);

const props = defineProps<{
    id: string;
    embed?: boolean;
    workflowInfo: StoredWorkflowDetailed;
}>();

const userStore = useUserStore();

const downloadUrl = computed(() => withPrefix(`/api/workflows/${props.id}/download?format=json-download`));
const importUrl = computed(() => withPrefix(`/workflow/imp?id=${props.id}`));
const runUrl = computed(() => withPrefix(`/workflows/run?id=${props.id}`));

const viewUrl = computed(() => withPrefix(`/published/workflow?id=${props.id}`));

const sharedWorkflow = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflowInfo.owner);
});

const editButtonTitle = computed(() => {
    if (userStore.isAnonymous) {
        return "Log in to edit Workflow";
    } else {
        if (props.workflowInfo.deleted) {
            return "You cannot edit a deleted workflow. Restore it first.";
        } else {
            return "Edit Workflow";
        }
    }
});

function logInTitle(title: string) {
    if (userStore.isAnonymous) {
        return `Log in to ${title}`;
    } else {
        return title;
    }
}
</script>

<template>
    <span>
        <BButton
            v-b-tooltip.hover.noninteractive
            title="Download workflow in .ga format"
            variant="outline-primary"
            size="md"
            :href="downloadUrl">
            <FontAwesomeIcon :icon="faDownload" />
            Download
        </BButton>

        <BButton
            v-if="!props.embed && sharedWorkflow"
            :href="importUrl"
            :disabled="userStore.isAnonymous"
            :title="logInTitle('Import Workflow')"
            data-description="workflow import"
            target="_blank"
            variant="outline-primary"
            size="md">
            <FontAwesomeIcon :icon="faEdit" />
            Import
        </BButton>

        <BButton
            v-else-if="!props.embed && !sharedWorkflow"
            v-b-tooltip.hover.noninteractive
            :disabled="workflowInfo.deleted"
            class="workflow-edit-button"
            :title="editButtonTitle"
            variant="outline-primary"
            size="md"
            :to="`/workflows/edit?id=${workflowInfo.id}`">
            <FontAwesomeIcon :icon="faEdit" fixed-width />
            Edit
        </BButton>

        <BButton
            v-if="!props.embed"
            :to="runUrl"
            :disabled="userStore.isAnonymous"
            :title="logInTitle('Run Workflow')"
            variant="primary"
            size="md">
            <FontAwesomeIcon :icon="faPlay" />
            Run
        </BButton>

        <BButton
            v-if="props.embed"
            :href="viewUrl"
            target="blank"
            variant="primary"
            size="md"
            class="view-button font-weight-bold">
            <FontAwesomeIcon :icon="['gxd', 'galaxyLogo']" />
            View In Galaxy
        </BButton>
    </span>
</template>
