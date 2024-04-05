<script setup lang="ts">
import { computed } from "vue";

interface Props {
    id: string;
    value?: string;
    area?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string | undefined): void;
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
