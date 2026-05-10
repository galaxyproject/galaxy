<script setup lang="ts">
import { faDownload, faEdit, faLink, faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButtonGroup } from "bootstrap-vue";
import { computed } from "vue";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getFullAppUrl } from "@/app/utils";
import { galaxyLogo } from "@/components/icons/galaxyIcons";
import { useUserStore } from "@/stores/userStore";
import { copy } from "@/utils/clipboard";
import { withPrefix } from "@/utils/redirect";

import GButton from "@/components/BaseComponents/GButton.vue";

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

const fullLink = computed(() => getFullAppUrl(`published/workflow?id=${props.id}`));

const sharedWorkflow = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflowInfo.owner);
});

function copyLink() {
    copy(fullLink.value);
}

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
        <BButtonGroup>
            <GButton v-g-tooltip.hover title="Download workflow in .ga format" color="blue" outline :href="downloadUrl">
                <FontAwesomeIcon :icon="faDownload" />
                Download
            </GButton>
            <GButton v-g-tooltip.hover title="Copy link to workflow" color="blue" outline @click="copyLink">
                <FontAwesomeIcon :icon="faLink" />
            </GButton>
        </BButtonGroup>

        <GButton
            v-if="!props.embed && sharedWorkflow"
            :href="importUrl"
            :disabled="userStore.isAnonymous"
            :title="logInTitle('Import Workflow')"
            data-description="workflow import"
            target="_blank"
            color="blue"
            outline>
            <FontAwesomeIcon :icon="faEdit" />
            Import
        </GButton>

        <GButton
            v-else-if="!props.embed && !sharedWorkflow"
            v-g-tooltip.hover
            :disabled="workflowInfo.deleted"
            class="workflow-edit-button"
            :title="editButtonTitle"
            color="blue"
            outline
            :to="`/workflows/edit?id=${workflowInfo.id}`">
            <FontAwesomeIcon :icon="faEdit" fixed-width />
            Edit
        </GButton>

        <GButton
            v-if="!props.embed"
            :to="runUrl"
            :disabled="userStore.isAnonymous"
            :title="logInTitle('Run Workflow')"
            color="blue">
            <FontAwesomeIcon :icon="faPlay" />
            Run
        </GButton>

        <GButton v-if="props.embed" :href="viewUrl" target="blank" color="blue" class="view-button font-weight-bold">
            <FontAwesomeIcon :icon="galaxyLogo" />
            View In Galaxy
        </GButton>
    </span>
</template>
