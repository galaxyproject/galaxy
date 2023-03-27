<script lang="ts" setup>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { computed } from "vue";

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
    <span v-b-tooltip.hover class="stored-how" :title="title">{{ text }}</span>
</template>

<style scoped>
/* Give visual indication of mouseover info */
.stored-how {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>
