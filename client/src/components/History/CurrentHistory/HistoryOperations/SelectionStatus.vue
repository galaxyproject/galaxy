<script setup lang="ts">
import { BButton, BButtonGroup } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    selectionSize: number;
}

const props = defineProps<Props>();

const emit = defineEmits(["select-all", "reset-selection"]);

const hasSelection = computed(() => {
    return props.selectionSize > 0;
});

function selectAll() {
    emit("select-all");
}
function resetSelection() {
    emit("reset-selection");
}
</script>

<template>
    <BButtonGroup size="sm">
        <BButton
            v-if="hasSelection"
            v-b-tooltip.hover
            title="Clear selection"
            variant="link"
            data-test-id="clear-btn"
            @click="resetSelection">
            <span class="fa fa-fw fa-times" />
        </BButton>

        <BButton v-else variant="link" data-test-id="select-all-btn" @click="selectAll">
            <span>Select All</span>
        </BButton>
    </BButtonGroup>
</template>
