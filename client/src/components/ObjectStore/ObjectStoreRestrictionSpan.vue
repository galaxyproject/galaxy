<script setup lang="ts">
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
        return "This dataset is stored in a restricted storage location. It can not be shared or published.";
    } else {
        return "This dataset is stored in an unrestricted storage location. With sufficient Galaxy permissions, this dataset can be published or shared.";
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
