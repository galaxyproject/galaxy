<script setup lang="ts">
import { computed } from "vue";

import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

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
    <GButtonGroup>
        <GButton
            v-if="hasSelection"
            v-g-tooltip.hover
            :title="localize('Clear selection')"
            transparent
            size="small"
            data-test-id="clear-btn"
            @click="resetSelection">
            <span class="fa fa-fw fa-times" />
        </GButton>

        <GButton v-else transparent color="blue" size="small" data-test-id="select-all-btn" @click="selectAll">
            <span v-localize>Select All</span>
        </GButton>
    </GButtonGroup>
</template>
