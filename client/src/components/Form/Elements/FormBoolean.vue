<script setup lang="ts">
import { computed } from "vue";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

export interface FormBooleanProps {
    value?: boolean | string | null;
    noLabel?: boolean;
}

const props = defineProps<FormBooleanProps>();
const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

const currentValue = computed({
    get() {
        return String(props.value).toLowerCase() === "true";
    },
    set(newValue) {
        emit("input", newValue);
    },
});

const label = computed(() => (currentValue.value ? "Yes" : "No"));
</script>

<template>
    <GCheckbox v-model="currentValue" class="no-highlight" switch>
        <!-- No slot at all without a label, so GCheckbox renders no empty label span -->
        <template v-if="!props.noLabel" v-slot>
            <span v-localize>{{ label }}</span>
        </template>
    </GCheckbox>
</template>
