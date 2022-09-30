<script setup>
import StatelessTags from "./StatelessTags.vue";
import { watch } from "vue";
import { useUserTags } from "composables/user";

const props = defineProps({
    value: Array,
    disabled: Boolean,
});

const { userTags } = useUserTags();

watch(
    () => userTags.value,
    (tags) => console.log(tags)
);
</script>

<template>
    <StatelessTags :value="props.value" :options="userTags" :disabled="props.disabled" />
</template>
