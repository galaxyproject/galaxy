<script setup lang="ts">
import { BInputGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import { COMMON_FILTERS, isValidFilter } from "@/components/Collections/pairing";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

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
    },
);
watch(
    () => props.reverseFilter,
    () => {
        currentReverseFilter.value = props.reverseFilter;
    },
);

function resync() {
    emit("on-update", currentForwardFilter.value, currentReverseFilter.value);
}

watch(currentForwardFilter, resync);
watch(currentReverseFilter, resync);
</script>

<template>
    <BInputGroup size="lg">
        <template v-slot:prepend>
            <GDropdown text="Filters" variant="info">
                <GDropdownItem
                    v-for="([forward, reverse], index) of COMMON_FILTERS"
                    :key="index"
                    @click="update(forward, reverse)">
                    {{ forward }} / {{ reverse }}
                </GDropdownItem>
                <GDropdownItem @click="update('', '')">
                    <i>Clear All Filtering</i>
                </GDropdownItem>
            </GDropdown>
        </template>

        <GFormInput v-model="currentForwardFilter" :state="isValidFilter(currentForwardFilter) ? null : false" />
        <GFormInput v-model="currentReverseFilter" :state="isValidFilter(currentReverseFilter) ? null : false" />
    </BInputGroup>
</template>
