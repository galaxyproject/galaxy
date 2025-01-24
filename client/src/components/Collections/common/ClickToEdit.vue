<script setup lang="ts">
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

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

const computedValue = computed(() => props.value);

watch(
    () => editable.value,
    (value) => {
        if (!value) {
            emit("input", localValue.value);
        }
    }
);
</script>

<template>
    <div v-if="editable">
        <input
            id="click-to-edit-input"
            v-model="localValue"
            tabindex="0"
            contenteditable
            @blur.prevent.stop="editable = false"
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
        class="click-to-edit-label"
        tabindex="0"
        @keyup.enter="editable = true"
        @click.stop="editable = true">
        <span v-if="computedValue">{{ computedValue }}</span>
        <i v-else>{{ title }}</i>
    </label>
</template>

<style scoped lang="scss">
.click-to-edit-label {
    cursor: text;
    &:hover > * {
        text-decoration: underline;
    }
}
</style>
