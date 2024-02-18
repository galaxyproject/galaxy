<script setup lang="ts">
import BootstrapVue from "bootstrap-vue";
import Vue, { computed } from "vue";

Vue.use(BootstrapVue);

const props = defineProps({
    isPrivate: Boolean,
});

const text = computed(() => (props.isPrivate ? "private" : "unrestricted"));
const title = computed(() => {
    if (props.isPrivate) {
        return "This dataset is stored on storage restricted to a single user. It can not be shared, published, or added to Galaxy data libraries.";
    } else {
        return "This dataset is stored on unrestricted storage. With sufficient Galaxy permissions, this dataset can be published, shared, or added to Galaxy data libraries.";
    }
});
</script>

<template>
    <span v-b-tooltip.hover class="stored-how object-store-help-on-hover" :title="title">{{ text }}</span>
</template>

<style scoped>
@import "./style.css";
</style>
