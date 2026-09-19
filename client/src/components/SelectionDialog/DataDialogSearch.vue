<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    value: string;
    title?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: "",
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const filter = computed({
    get: () => {
        return props.value;
    },
    set: (newValue: string) => {
        emit("input", newValue);
    },
});

const placeholder = computed(() => `search ${props.title.toLowerCase()}`);

function reset() {
    filter.value = "";
}
</script>

<template>
    <BInputGroup class="w-100">
        <BFormInput v-model="filter" :placeholder="placeholder" debounce="500" />
        <BInputGroupAppend>
            <GButton :disabled="!filter" @click="reset"><FontAwesomeIcon :icon="faTimes" /></GButton>
        </BInputGroupAppend>
    </BInputGroup>
</template>
