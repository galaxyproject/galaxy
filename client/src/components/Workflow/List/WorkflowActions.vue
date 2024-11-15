<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import {
    faCaretDown,
    faCopy,
    faDownload,
    faExternalLinkAlt,
    faFileExport,
    faLink,
    faPlay,
    faShareAlt,
    faSpinner,
    faStar,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BDropdown, BDropdownItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useUserStore } from "@/stores/userStore";

import { useWorkflowActions } from "./useWorkflowActions";

interface Props {
    workflow: any;
    published?: boolean;
    editor?: boolean;
    current?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    published: false,
    editor: false,
    current: false,
});

const emit = defineEmits<{
    (e: "refreshList", overlayLoading?: boolean): void;
    (e: "dropdown", open: boolean): void;
}>();

const { bookmarkLoading, deleteWorkflow, toggleBookmark, copyPublicLink, copyWorkflow, downloadUrl } =
    useWorkflowActions(
        computed(() => props.workflow),
        () => emit("refreshList", true)
    );

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflow.owner);
});

const sourceType = computed(() => {
    if (props.workflow.source_metadata?.url) {
        return "url";
    } else if (props.workflow.source_metadata?.trs_server) {
        return `trs_${props.workflow.source_metadata?.trs_server}`;
    } else {
        return "";
    }
});

const runPath = computed(
    () =>
        `/workflows/run?id=${props.workflow.id}${
            props.workflow.version !== undefined ? `&version=${props.workflow.version}` : ""
        }`
);
</script>

<template>
    <div class="workflow-actions">
        <BButtonGroup>
            <BButton
                v-if="!props.workflow.deleted && !props.workflow.show_in_tool_panel"
                v-b-tooltip.hover.noninteractive
                class="workflow-bookmark-button-add inline-icon-button"
                variant="link"
                title="Add to bookmarks"
                tooltip="Add to bookmarks. This workflow will appear in the left tool panel."
                size="sm"
                @click="toggleBookmark(true)">
                <FontAwesomeIcon v-if="!bookmarkLoading" :icon="farStar" fixed-width />
                <FontAwesomeIcon v-else :icon="faSpinner" spin fixed-width />
            </BButton>
            <BButton
                v-else-if="!props.workflow.deleted && props.workflow.show_in_tool_panel"
                v-b-tooltip.hover.noninteractive
                class="workflow-bookmark-button-remove inline-icon-button"
                variant="link"
                title="Remove bookmark"
                size="sm"
                @click="toggleBookmark(false)">
                <FontAwesomeIcon v-if="!bookmarkLoading" :icon="faStar" fixed-width />
                <FontAwesomeIcon v-else :icon="faSpinner" spin fixed-width />
            </BButton>

            <BDropdown
                v-b-tooltip.top.noninteractive
                :data-workflow-actions-dropdown="workflow.id"
                right
                no-caret
                class="workflow-actions-dropdown"
                title="Workflow actions"
                toggle-class="inline-icon-button"
                variant="link"
                @show="() => emit('dropdown', true)"
                @hide="() => emit('dropdown', false)">
                <template v-slot:button-content>
                    <FontAwesomeIcon :icon="faCaretDown" fixed-width />
                </template>

                <template v-if="props.editor">
                    <BDropdownItem :to="runPath" title="Run workflow" size="sm" variant="link">
                        <FontAwesomeIcon :icon="faPlay" fixed-width />
                        Run
                    </BDropdownItem>

                    <BDropdownItem
                        v-if="props.workflow.published"
                        size="sm"
                        title="Copy link to workflow"
                        @click="copyPublicLink">
                        <FontAwesomeIcon :icon="faLink" fixed-width />
                        Link to Workflow
                    </BDropdownItem>

                    <BDropdownItem v-if="!isAnonymous && !shared" size="sm" title="Copy workflow" @click="copyWorkflow">
                        <FontAwesomeIcon :icon="faCopy" fixed-width />
                        Copy
                    </BDropdownItem>

                    <BDropdownItem
                        size="sm"
                        title="Download workflow in .ga format"
                        target="_blank"
                        :href="downloadUrl">
                        <FontAwesomeIcon :icon="faDownload" fixed-width />
                        Download
                    </BDropdownItem>

                    <BDropdownItem
                        v-if="!isAnonymous && !shared"
                        size="sm"
                        title="Share"
                        :to="`/workflows/sharing?id=${workflow.id}`">
                        <FontAwesomeIcon :icon="faShareAlt" fixed-width />
                        Share
                    </BDropdownItem>
                </template>

                <BDropdownItem
                    v-if="!isAnonymous && !shared && !props.workflow.deleted && !props.current"
                    class="workflow-delete-button"
                    title="Delete workflow"
                    size="sm"
                    @click="deleteWorkflow">
                    <FontAwesomeIcon :icon="faTrash" fixed-width />
                    Delete
                </BDropdownItem>

                <BDropdownItem
                    v-if="sourceType.includes('trs')"
                    class="source-trs-button"
                    :title="`View on ${props.workflow.source_metadata?.trs_server}`"
                    size="sm"
                    :href="`https://dockstore.org/workflows${props.workflow?.source_metadata?.trs_tool_id?.slice(9)}`"
                    target="_blank">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    View on Dockstore
                </BDropdownItem>

                <BDropdownItem
                    v-if="sourceType == 'url'"
                    class="workflow-view-external-link-button"
                    title="View external link"
                    size="sm"
                    :href="props.workflow.source_metadata?.url"
                    target="_blank">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    View external link
                </BDropdownItem>

                <BDropdownItem
                    v-if="!props.workflow.deleted"
                    class="workflow-export-button"
                    title="Export"
                    size="sm"
                    :to="`/workflows/export?id=${props.workflow.id}`">
                    <FontAwesomeIcon :icon="faFileExport" fixed-width />
                    Export
                </BDropdownItem>
            </BDropdown>
        </BButtonGroup>
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    display: flex;
    align-items: center;
}
</style>
