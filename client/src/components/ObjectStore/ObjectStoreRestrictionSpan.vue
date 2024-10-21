<script setup lang="ts">
import BootstrapVue from "bootstrap-vue";
import Vue, { computed } from "vue";

Vue.use(BootstrapVue);

const props = defineProps({
    isPrivate: Boolean,
});

const text = computed(() => (props.isPrivate ? "private" : "sharable"));
const title = computed(() => {
    if (props.isPrivate) {
        return "This dataset is stored on storage restricted to a single user. It cannot be shared, published, or added to Galaxy data libraries.";
    } else {
        return "This dataset is stored on storage that allows standard Galaxy sharing features. If you have sufficient Galaxy permissions to this dataset - the dataset can be published, shared, or added to data libraries within Galaxy.";
    }
});
</script>

<template>
    <span v-b-tooltip.hover class="stored-how object-store-help-on-hover" :title="title">{{ text }}</span>
</template>

<style scoped>
@import "./style.css";
</style>
