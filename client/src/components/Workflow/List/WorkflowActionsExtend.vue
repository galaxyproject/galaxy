<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faDownload, faLink, faShareAlt, faTrashRestore } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { copyWorkflow, undeleteWorkflow } from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { copy } from "@/utils/clipboard";
import { withPrefix } from "@/utils/redirect";
import { getFullAppUrl } from "@/utils/utils";

library.add(faCopy, faDownload, faLink, faShareAlt, faTrashRestore);

interface Props {
    workflow: any;
    published?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    published: false,
});

const emit = defineEmits<{
    (e: "refreshList", overlayLoading?: boolean): void;
}>();

const userStore = useUserStore();
const { confirm } = useConfirmDialog();
const { isAnonymous } = storeToRefs(useUserStore());

const downloadUrl = computed(() => {
    return withPrefix(`/api/workflows/${props.workflow.id}/download?format=json-download`);
});

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflow.owner);
});

async function onCopy() {
    const confirmed = await confirm("Are you sure you want to make a copy of this workflow?", "Copy workflow");

    if (confirmed) {
        await copyWorkflow(props.workflow.id, props.workflow.owner);
        emit("refreshList", true);
        Toast.success("Workflow copied");
    }
}

async function onRestore() {
    const confirmed = await confirm("Are you sure you want to restore this workflow?", "Restore workflow");

    if (confirmed) {
        await undeleteWorkflow(props.workflow.id);
        emit("refreshList", true);
        Toast.info("Workflow restored");
    }
}

const relativeLink = computed(() => {
    return `/published/workflow?id=${props.workflow.id}`;
});

const fullLink = computed(() => {
    return getFullAppUrl(relativeLink.value.substring(1));
});

function onCopyPublicLink() {
    copy(fullLink.value);
    Toast.success("Link to workflow copied");
}
</script>

<template>
    <div class="workflow-actions-extend flex-gapx-1">
        <BButtonGroup>
            <BButton
                v-if="workflow.published && !workflow.deleted"
                id="workflow-copy-public-button"
                v-b-tooltip.hover.noninteractive
                size="sm"
                title="Copy link to workflow"
                variant="outline-primary"
                @click="onCopyPublicLink">
                <FontAwesomeIcon :icon="faLink" fixed-width />
                <span class="compact-view">Link to Workflow</span>
            </BButton>

            <BButton
                v-if="!isAnonymous && !shared && !workflow.deleted"
                id="workflow-copy-button"
                v-b-tooltip.hover.noninteractive
                size="sm"
                title="Copy"
                variant="outline-primary"
                @click="onCopy">
                <FontAwesomeIcon :icon="faCopy" fixed-width />
                <span class="compact-view">Copy</span>
            </BButton>

            <BButton
                v-if="!workflow.deleted"
                id="workflow-download-button"
                v-b-tooltip.hover.noninteractive
                size="sm"
                title="Download workflow in .ga format"
                variant="outline-primary"
                :href="downloadUrl">
                <FontAwesomeIcon :icon="faDownload" fixed-width />
                <span class="compact-view">Download</span>
            </BButton>

            <BButton
                v-if="!isAnonymous && !shared && !workflow.deleted"
                id="workflow-share-button"
                v-b-tooltip.hover.noninteractive
                size="sm"
                title="Share"
                variant="outline-primary"
                :to="`/workflows/sharing?id=${workflow.id}`">
                <FontAwesomeIcon :icon="faShareAlt" fixed-width />
                <span class="compact-view">Share</span>
            </BButton>

            <BButton
                v-if="workflow.deleted"
                id="restore-button"
                v-b-tooltip.hover.noninteractive
                size="sm"
                title="Restore"
                variant="outline-primary"
                @click="onRestore">
                <FontAwesomeIcon :icon="faTrashRestore" fixed-width />
                <span class="compact-view">Restore</span>
            </BButton>
        </BButtonGroup>
    </div>
</template>

<style scoped lang="scss">
@import "breakpoints.scss";

.workflow-actions-extend {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    justify-content: flex-end;

    @container (max-width: #{$breakpoint-md}) {
        .compact-view {
            display: none;
        }
    }
}
</style>
