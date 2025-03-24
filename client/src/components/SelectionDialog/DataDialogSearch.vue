<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed } from "vue";

library.add(faTimes);

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

const placeholder = computed(() => `搜索 ${props.title.toLowerCase()}`);
</script>

<template>
    <BInputGroup class="w-100">
        <BFormInput v-model="filter" :placeholder="placeholder" debounce="500" />
        <BInputGroupAppend>
            <BButton :disabled="!filter" @click="filter = ''"><FontAwesomeIcon icon="times" /></BButton>
        </BInputGroupAppend>
    </BInputGroup>
</template>
