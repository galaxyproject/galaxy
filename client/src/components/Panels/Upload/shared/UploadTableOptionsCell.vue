<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";

interface Props {
    /** Whether to convert spaces to tabs */
    spaceToTab: boolean;
    /** Whether to convert to POSIX line endings */
    toPosixLines: boolean;
    /** Whether to defer data fetching (optional, for URLs) */
    deferred?: boolean;
    /** Whether to show the deferred checkbox */
    showDeferred?: boolean;
}

withDefaults(defineProps<Props>(), {
    deferred: false,
    showDeferred: false,
});

const emit = defineEmits<{
    (e: "updateSpaceToTab", value: boolean): void;
    (e: "updateToPosixLines", value: boolean): void;
    (e: "updateDeferred", value: boolean): void;
}>();

function updateSpaceToTab(value: boolean) {
    emit("updateSpaceToTab", value);
}

function updateToPosixLines(value: boolean) {
    emit("updateToPosixLines", value);
}

function updateDeferred(value: boolean) {
    emit("updateDeferred", value);
}
</script>

<template>
    <div class="d-flex align-items-center">
        <BFormCheckbox
            v-b-tooltip.hover.noninteractive
            :checked="spaceToTab"
            size="sm"
            class="mr-2"
            title="Convert spaces to tab characters"
            @change="updateSpaceToTab">
            <span class="small">Spaces→Tabs</span>
        </BFormCheckbox>
        <BFormCheckbox
            v-b-tooltip.hover.noninteractive
            :checked="toPosixLines"
            size="sm"
            :class="{ 'mr-2': showDeferred }"
            title="Convert line endings to POSIX standard"
            @change="updateToPosixLines">
            <span class="small">POSIX</span>
        </BFormCheckbox>
        <BFormCheckbox
            v-if="showDeferred"
            v-b-tooltip.hover.noninteractive
            :checked="deferred"
            size="sm"
            title="Galaxy will store a reference and fetch data only when needed by a tool"
            @change="updateDeferred">
            <span class="small">Deferred</span>
        </BFormCheckbox>
    </div>
</template>
