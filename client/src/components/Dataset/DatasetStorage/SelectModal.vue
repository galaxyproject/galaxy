<script setup lang="ts">
import { ref, watch } from "vue";

interface SelectModalProps {
    value: boolean;
    title: string;
}

const props = defineProps<SelectModalProps>();

const show = ref(props.value);

watch(props, () => {
    show.value = props.value;
});

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

watch(show, () => {
    emit("input", show.value);
});
</script>

<template>
    <b-modal v-model="show" hide-footer>
        <template v-slot:modal-title>
            <h2>{{ title }}</h2>
        </template>
        <slot />
    </b-modal>
</template>
