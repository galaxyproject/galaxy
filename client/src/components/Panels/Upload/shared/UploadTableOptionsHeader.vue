<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";

interface Props {
    /** All items have spaceToTab enabled */
    allSpaceToTab: boolean;
    /** Some but not all items have spaceToTab enabled */
    spaceToTabIndeterminate: boolean;
    /** All items have toPosixLines enabled */
    allToPosixLines: boolean;
    /** Some but not all items have toPosixLines enabled */
    toPosixLinesIndeterminate: boolean;
    /** Whether to show the deferred checkbox (for URL uploads) */
    showDeferred?: boolean;
    /** All items have deferred enabled */
    allDeferred?: boolean;
    /** Some but not all items have deferred enabled */
    deferredIndeterminate?: boolean;
}

withDefaults(defineProps<Props>(), {
    showDeferred: false,
    allDeferred: false,
    deferredIndeterminate: false,
});

const emit = defineEmits<{
    (e: "toggle-space-to-tab"): void;
    (e: "toggle-to-posix-lines"): void;
    (e: "toggle-deferred"): void;
}>();

function handleToggleSpaceToTab() {
    emit("toggle-space-to-tab");
}

function handleToggleToPosixLines() {
    emit("toggle-to-posix-lines");
}

function handleToggleDeferred() {
    emit("toggle-deferred");
}
</script>

<template>
    <div class="options-header">
        <span class="options-title">Upload Settings</span>
        <div class="d-flex align-items-center">
            <BFormCheckbox
                v-b-tooltip.hover.noninteractive
                :checked="allSpaceToTab"
                :indeterminate="spaceToTabIndeterminate"
                size="sm"
                class="mr-2"
                title="Toggle all: Convert spaces to tab characters"
                @change="handleToggleSpaceToTab">
                <span class="small">Spaces→Tabs</span>
            </BFormCheckbox>
            <BFormCheckbox
                v-b-tooltip.hover.noninteractive
                :checked="allToPosixLines"
                :indeterminate="toPosixLinesIndeterminate"
                size="sm"
                class="mr-2"
                title="Toggle all: Convert line endings to POSIX standard"
                @change="handleToggleToPosixLines">
                <span class="small">POSIX</span>
            </BFormCheckbox>
            <BFormCheckbox
                v-if="showDeferred"
                v-b-tooltip.hover.noninteractive
                :checked="allDeferred"
                :indeterminate="deferredIndeterminate"
                size="sm"
                title="Toggle all: Galaxy will store a reference and fetch data only when needed by a tool"
                @change="handleToggleDeferred">
                <span class="small">Deferred</span>
            </BFormCheckbox>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "../shared/upload-table-shared.scss";
</style>
