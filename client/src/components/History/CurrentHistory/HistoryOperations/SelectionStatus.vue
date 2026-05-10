<script setup lang="ts">
import { BButtonGroup } from "bootstrap-vue";
import { computed } from "vue";

import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

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
        <GButton
            v-if="hasSelection"
            v-g-tooltip.hover
            :title="localize('Clear selection')"
            transparent
            data-test-id="clear-btn"
            @click="resetSelection">
            <span class="fa fa-fw fa-times" />
        </GButton>

        <GButton v-else transparent data-test-id="select-all-btn" @click="selectAll">
            <span v-localize>Select All</span>
        </GButton>
    </BButtonGroup>
</template>
