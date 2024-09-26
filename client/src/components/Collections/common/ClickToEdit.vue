<script setup lang="ts">
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { ref, watch } from "vue";

interface Props {
    value: string;
    title?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const editable = ref(false);
const localValue = ref(props.value);

watch(
    () => editable.value,
    (value) => {
        if (!value) {
            emit("input", localValue.value);
            localValue.value = props.value;
        }
    }
);
</script>

<template>
    <div v-if="editable">
        <input
            id="click-to-edit-input"
            v-model="localValue"
            class="click-to-edit-input"
            tabindex="0"
            contenteditable
            @blur="editable = false"
            @keyup.prevent.stop.enter="editable = false"
            @keyup.prevent.stop.escape="editable = false"
            @click.prevent.stop />
        <BButton class="p-0" style="border: none" variant="link" size="sm" @click.prevent.stop="editable = false">
            <FontAwesomeIcon :icon="faSave" />
        </BButton>
    </div>

    <label
        v-else
        role="button"
        for="click-to-edit-input"
        tabindex="0"
        @keyup.enter="editable = true"
        @click.stop="editable = true">
        {{ localValue }}
    </label>
</template>

<style scoped lang="scss">
.click-to-edit-input {
    line-height: 1 !important;
}
</style>
