<script setup lang="ts">
interface Props {
    // TODO: Define the type of the element
    element: any;
}

defineProps<Props>();

const emit = defineEmits<{
    // TODO: Define the type of the element
    (event: "element-is-selected", element: any): void;
}>();
</script>

<template>
    <li class="dataset unpaired" @click="emit('element-is-selected', element)">
        <label>
            {{ element.name }}
        </label>
    </li>
</template>
