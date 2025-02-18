<script setup lang="ts">
import { BDropdown, BDropdownItem, BFormInput, BInputGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import { COMMON_FILTERS } from "@/components/Collections/pairing";

interface Props {
    forwardFilter: string;
    reverseFilter: string;
}

const emit = defineEmits<{
    (e: "on-update", forwardFilter: string, reverseFilter: string): void;
}>();

function update(forward: string, reverse: string) {
    emit("on-update", forward, reverse);
}

const props = defineProps<Props>();

const currentForwardFilter = ref(props.forwardFilter);
const currentReverseFilter = ref(props.reverseFilter);

watch(
    () => props.forwardFilter,
    () => {
        currentForwardFilter.value = props.forwardFilter;
    }
);
watch(
    () => props.reverseFilter,
    () => {
        currentReverseFilter.value = props.reverseFilter;
    }
);

function resync() {
    emit("on-update", currentForwardFilter.value, currentReverseFilter.value);
}

watch(currentForwardFilter, resync);
watch(currentForwardFilter, resync);
</script>

<template>
    <BInputGroup size="lg">
        <template v-slot:prepend>
            <BDropdown text="Filters" variant="info">
                <BDropdownItem
                    v-for="([forward, reverse], index) of COMMON_FILTERS"
                    :key="index"
                    @click="update(forward, reverse)">
                    {{ forward }} / {{ reverse }}
                </BDropdownItem>
                <BDropdownItem @click="update('', '')">
                    <i>Clear All Filtering</i>
                </BDropdownItem>
            </BDropdown>
        </template>

        <BFormInput v-model="currentForwardFilter"></BFormInput>
        <BFormInput v-model="currentReverseFilter"></BFormInput>
    </BInputGroup>
</template>
