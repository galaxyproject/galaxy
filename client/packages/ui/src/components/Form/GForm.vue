<script setup lang="ts">
import { ref } from "vue";

// Declared so a parent's `@submit.prevent` gets the native event even when this runs
// under @vue/compat, where undeclared listeners don't fall through to the root element.
const emit = defineEmits<{
    (e: "submit", event: SubmitEvent): void;
}>();

const form = ref<HTMLFormElement>();

function checkValidity() {
    if (!form.value) {
        throw new TypeError("GForm: form element is not mounted");
    }
    return form.value.checkValidity();
}

defineExpose({
    checkValidity,
});
</script>

<template>
    <form ref="form" @submit="emit('submit', $event as SubmitEvent)">
        <slot></slot>
    </form>
</template>
