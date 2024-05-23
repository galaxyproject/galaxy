<script setup lang="ts">
import { computed } from "vue";

interface Props {
    id: string;
    area?: boolean;
    value?: string | number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string | number | undefined): void;
}>();

const currentValue = computed({
    get() {
        return props.value;
    },
    set(val) {
        emit("input", val);
    },
});
</script>

<template>
    <textarea v-if="area" :id="id" v-model="currentValue" class="ui-textarea" />

    <input v-else :id="id" v-model="currentValue" class="ui-input" />
</template>
