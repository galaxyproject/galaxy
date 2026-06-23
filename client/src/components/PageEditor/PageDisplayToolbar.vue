<script setup lang="ts">
import {
    faArrowLeft,
    faEdit,
    faEye,
    faHistory,
    faInfo,
    faPen,
    faSave,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { PAGE_LABELS } from "@/components/Page/constants";
import { usePageEditorStore } from "@/stores/pageEditorStore.js";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import RenameModal from "../Common/RenameModal.vue";

const props = defineProps<{
    labels: (typeof PAGE_LABELS)[keyof typeof PAGE_LABELS];
    mode: "editor" | "display";
}>();

const pageEditorStore = usePageEditorStore();
const { canSave, currentPage, currentTitle, revisionCount, showRevisions, isDirty, isSaving } =
    storeToRefs(pageEditorStore);

const emit = defineEmits<{
    (e: "back"): void;
    (e: "edit"): void;
    (e: "preview"): void;
}>();

const showRename = ref(false);

const currentEntity = computed(() => {
    return props.labels.entityName.toLowerCase();
});

const saveDisabledTitle = computed(() => {
    if (props.mode === "display") {
        return `Currently previewing this ${currentEntity.value}. Click 'Edit' to make changes and enable saving.`;
    }
    if (isSaving.value) {
        return `This ${currentEntity.value} is being saved`;
    }
    if (!canSave.value) {
        return `There are no changes to save to this ${currentEntity.value}`;
    }
    return "";
});

async function handleSave() {
    await pageEditorStore.savePage();
}

function handleTitleChange(newTitle: string): Promise<void> {
    return new Promise((resolve) => {
        pageEditorStore.updateTitle(newTitle);
        resolve();
    });
}
</script>

<template>
    <div class="page-display-toolbar border-bottom" :data-description="`page ${props.mode} toolbar`">
        <div class="d-flex align-items-center flex-gapx-1 title-section">
            <FontAwesomeIcon :icon="props.labels.titleIcon" fixed-width />
            <b class="page-title" :data-description="`page ${props.mode} title`">
                {{ currentTitle || props.labels.defaultTitle }}
            </b>
            <GButton
                v-if="props.mode === 'editor'"
                inline
                transparent
                data-description="page rename button"
                :title="`Rename this ${currentEntity}`"
                @click="showRename = true">
                <FontAwesomeIcon :icon="faPen" />
            </GButton>
        </div>

        <div class="d-flex align-items-center flex-gapx-1 flex-shrink-0">
            <span
                v-if="isDirty"
                class="d-flex align-items-center flex-gapx-1 text-warning small"
                data-description="page unsaved indicator">
                <BBadge variant="warning" class="text-light">
                    <FontAwesomeIcon :icon="faInfo" />
                </BBadge>
                Unsaved
            </span>

            <GButton color="blue" transparent size="small" data-description="page back button" @click="emit('back')">
                <FontAwesomeIcon :icon="faArrowLeft" />
                {{ props.labels.editorBackLabel }}
            </GButton>

            <slot name="extra-actions" />

            <GButton
                v-if="props.mode === 'editor'"
                color="blue"
                outline
                :pressed="showRevisions"
                data-description="page revisions button"
                size="small"
                @click="pageEditorStore.toggleRevisions">
                <FontAwesomeIcon :icon="faHistory" />
                Revisions
                <BBadge
                    v-if="revisionCount > 0"
                    variant="light"
                    style="top: 0"
                    data-description="page revision count badge">
                    {{ revisionCount }}
                </BBadge>
            </GButton>

            <GButtonGroup data-description="revision view mode toggle">
                <GButton
                    color="blue"
                    outline
                    :pressed="props.mode === 'editor'"
                    data-description="page edit button"
                    :disabled="currentPage?.deleted"
                    size="small"
                    @click="emit('edit')">
                    <FontAwesomeIcon :icon="faEdit" />
                    Edit
                </GButton>
                <GButton
                    color="blue"
                    outline
                    :pressed="props.mode === 'display'"
                    data-description="page preview button"
                    size="small"
                    @click="emit('preview')">
                    <FontAwesomeIcon :icon="faEye" />
                    Preview
                </GButton>
            </GButtonGroup>

            <GButton
                color="blue"
                data-description="page save button"
                :title="`Save ${props.labels.entityName}`"
                tooltip
                :disabled="props.mode === 'display' || !canSave"
                :disabled-title="saveDisabledTitle"
                size="small"
                @click="handleSave">
                <FontAwesomeIcon :icon="isSaving ? faSpinner : faSave" :spin="isSaving" />
                Save
            </GButton>
        </div>

        <RenameModal
            v-if="showRename"
            :item-type="currentEntity"
            :name="currentTitle || props.labels.defaultTitle"
            :rename-action="handleTitleChange"
            @close="showRename = false" />
    </div>
</template>

<style scoped>
.page-display-toolbar {
    background: var(--color-grey-100);
    display: flex;
    align-items: center;
    padding: 0.5rem 1rem;
    gap: 0.5rem;
    justify-content: space-between;
}
.title-section {
    min-width: 0;
    overflow: hidden;
}
.page-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
