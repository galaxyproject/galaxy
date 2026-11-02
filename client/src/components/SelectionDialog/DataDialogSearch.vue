<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";

defineOptions({
    compatConfig: { COMPONENT_V_MODEL: false },
});

interface Props {
    modelValue: string;
    title?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: "",
});

const emit = defineEmits<{
    (e: "update:modelValue", value: string): void;
}>();

const filter = computed({
    get: () => {
        return props.modelValue;
    },
    set: (newValue: string) => {
        emit("update:modelValue", newValue);
    },
});

const placeholder = computed(() => `search ${props.title.toLowerCase()}`);

function reset() {
    filter.value = "";
}
</script>

<template>
    <BInputGroup class="w-100">
        <BFormInput v-model="filter" :placeholder="placeholder" :aria-label="placeholder" debounce="500" />
        <BInputGroupAppend>
            <GButton aria-label="Clear search" :disabled="!filter" @click="reset"
                ><FontAwesomeIcon :icon="faTimes"
            /></GButton>
        </BInputGroupAppend>
    </BInputGroup>
</template>
