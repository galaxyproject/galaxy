<script setup lang="ts">
import {
    faCopy,
    faEyeSlash,
    faFile,
    faInfoCircle,
    faPen,
    faSignInAlt,
    faSpinner,
    faStop,
    faTrash,
    faTrashRestore,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
//@ts-ignore deprecated package without types (vue 2, remove this comment on vue 3 migration)
import { ScanEye } from "lucide-vue-next";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref } from "vue";

import { copyDataset } from "@/api/datasets";
import { useToast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

const props = defineProps({
    writable: { type: Boolean, default: true },
    isDataset: { type: Boolean, required: true },
    isDeleted: { type: Boolean, default: false },
    isHistoryItem: { type: Boolean, required: true },
    isVisible: { type: Boolean, default: true },
    state: { type: String, default: "" },
    itemUrls: { type: Object, required: true },
    isRunningInteractiveTool: { type: Boolean, default: false },
    interactiveToolId: { type: String, default: "" },
    itemId: { type: String, default: "" },
});

const emit = defineEmits<{
    (e: "display"): void;
    (e: "showCollectionInfo"): void;
    (e: "edit"): void;
    (e: "delete", recursive?: boolean): void;
    (e: "undelete"): void;
    (e: "unhide"): void;
}>();

const entryPointStore = useEntryPointStore();
const Toast = useToast();
const { currentHistoryId } = storeToRefs(useHistoryStore());
const errorMessage = ref("");
const deleteCollectionMenu: Ref<InstanceType<typeof GDropdown> | null> = ref(null);
const copyingCollection = ref(false);

const editButtonTitle = computed(() => (editDisabled.value ? "This dataset is not yet editable." : "Edit attributes"));
const editDisabled = computed(() =>
    ["discarded", "new", "upload", "queued", "running", "waiting"].includes(props.state),
);
const editUrl = computed(() => prependPath(props.itemUrls.edit));
const displayUrl = computed(() => (props.itemUrls.display ? prependPath(props.itemUrls.display) : undefined));

const isCollection = computed(() => !props.isDataset);

const canShowCollectionDetails = computed(() => props.itemUrls.showDetails);

// Used to ensure only top-level collections (HDCAs) can be copied
// Nested `DatasetCollectionElement` collections don't have their
// own `HistoryDatasetCollectionAssociation`, so only their individual
// dataset elements remain copyable once you drill into them.
const showCopyToCurrentHistory = computed(
    () => !props.writable && isCollection.value && props.isHistoryItem && !props.isDeleted && !!props.itemId,
);

const showCollectionDetailsUrl = computed(() => prependPath(props.itemUrls.showDetails));

function onDelete($event: MouseEvent) {
    if (props.isRunningInteractiveTool) {
        stopInteractiveTool();
    } else if (isCollection.value) {
        deleteCollectionMenu.value?.show();
    } else {
        onDeleteItem();
    }
}

async function stopInteractiveTool() {
    if (!props.interactiveToolId) {
        console.error("No interactive tool ID provided");
        return;
    }

    try {
        const root = getAppRoot();
        const url = `${root}api/entry_points/${props.interactiveToolId}`;
        await axios.delete(url);
        entryPointStore.removeEntryPoint(props.interactiveToolId);
    } catch (error) {
        console.error("Failed to stop interactive tool:", error);
        errorMessage.value = "Failed to stop interactive tool";
    }
}

function onDeleteItem() {
    emit("delete");
}

function onDeleteItemRecursively() {
    const recursive = true;
    emit("delete", recursive);
}

function onDisplay($event: MouseEvent) {
    // Wrap display handler to allow ctrl/meta click to open in new tab
    // instead of triggering display.
    if ($event.ctrlKey || $event.metaKey) {
        window.open(displayUrl.value, "_blank");
    } else {
        emit("display");
    }
}

async function copyToCurrentHistory() {
    copyingCollection.value = true;
    try {
        if (currentHistoryId.value) {
            await copyDataset(props.itemId, currentHistoryId.value, "dataset_collection");
            Toast.success(localize("Collection copied to the current history!"));
        } else {
            throw new Error(localize("No current history available to copy the collection to."));
        }
    } catch (error) {
        Toast.error(errorMessageAsString(error), localize("Failed to copy collection to the current history"));
    } finally {
        copyingCollection.value = false;
    }
}
</script>

<template>
    <span class="align-self-start btn-group align-items-baseline">
        <!-- Special case for collections -->
        <GButton
            v-if="isCollection && canShowCollectionDetails"
            v-g-tooltip.hover
            class="collection-job-details-btn px-1"
            :title="localize('Show Details')"
            size="small"
            transparent
            :href="showCollectionDetailsUrl"
            @click.prevent.stop="emit('showCollectionInfo')">
            <FontAwesomeIcon :icon="faInfoCircle" />
        </GButton>
        <!-- Common for all content items -->
        <GButton
            v-if="isDataset"
            v-g-tooltip.hover
            :title="localize('View')"
            tabindex="0"
            class="display-btn px-1"
            size="small"
            transparent
            :href="displayUrl"
            @click.prevent.stop="onDisplay($event)">
            <ScanEye absolute-stroke-width :size="16" />
        </GButton>
        <GButton
            v-if="writable && isHistoryItem"
            v-g-tooltip.hover
            :disabled="editDisabled"
            :title="localize(editButtonTitle)"
            tabindex="0"
            class="edit-btn px-1"
            size="small"
            transparent
            :href="editUrl"
            @click.prevent.stop="emit('edit')">
            <FontAwesomeIcon :icon="faPen" />
        </GButton>
        <GButton
            v-if="isRunningInteractiveTool"
            v-g-tooltip.hover
            class="delete-btn px-1"
            :title="localize('Stop this Interactive Tool')"
            size="small"
            transparent
            @click.stop="onDelete($event)">
            <FontAwesomeIcon :icon="faStop" />
        </GButton>
        <GButton
            v-else-if="writable && isHistoryItem && !isDeleted"
            v-g-tooltip.hover
            :tabindex="isDataset ? '0' : '-1'"
            class="delete-btn px-1"
            :title="localize('Delete')"
            size="small"
            transparent
            @click.stop="onDelete($event)">
            <FontAwesomeIcon v-if="isDataset" :icon="faTrash" />
            <GDropdown
                v-else
                ref="deleteCollectionMenu"
                size="sm"
                variant="link"
                no-caret
                toggle-class="p-0 m-0"
                :aria-label="localize('Delete')">
                <template v-slot:button-content>
                    <FontAwesomeIcon :icon="faTrash" />
                </template>
                <GDropdownItem title="Delete collection only" @click.prevent.stop="onDeleteItem">
                    <FontAwesomeIcon :icon="faFile" />
                    Collection only
                </GDropdownItem>
                <GDropdownItem title="Delete collection and elements" @click.prevent.stop="onDeleteItemRecursively">
                    <FontAwesomeIcon :icon="faCopy" />
                    Collection and elements
                </GDropdownItem>
            </GDropdown>
        </GButton>
        <GButton
            v-if="writable && isHistoryItem && isDeleted"
            v-g-tooltip.hover
            tabindex="0"
            class="undelete-btn px-1"
            :title="localize('Undelete')"
            size="small"
            transparent
            @click.stop="emit('undelete')">
            <FontAwesomeIcon :icon="faTrashRestore" />
        </GButton>
        <GButton
            v-if="writable && isHistoryItem && !isVisible"
            v-g-tooltip.hover
            tabindex="0"
            class="unhide-btn px-1"
            :title="localize('Unhide')"
            size="small"
            transparent
            @click.stop="emit('unhide')">
            <FontAwesomeIcon :icon="faEyeSlash" />
        </GButton>
        <GButton
            v-if="showCopyToCurrentHistory"
            v-g-tooltip.hover
            :disabled="copyingCollection"
            class="copy-to-current-history-btn px-1"
            :title="localize('Copy to Current History')"
            size="small"
            transparent
            @click.prevent.stop="copyToCurrentHistory">
            <FontAwesomeIcon :icon="copyingCollection ? faSpinner : faSignInAlt" :spin="copyingCollection" />
        </GButton>
    </span>
</template>

<style lang="css">
.dropdown-menu .dropdown-item {
    font-weight: normal;
}
</style>
```
