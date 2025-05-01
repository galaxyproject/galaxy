<script setup lang="ts">
import BootstrapVue from "bootstrap-vue";
import Vue, { computed } from "vue";

Vue.use(BootstrapVue);

const props = defineProps({
    isPrivate: Boolean,
});

const text = computed(() => (props.isPrivate ? "私有" : "可共享"));
const title = computed(() => {
    if (props.isPrivate) {
        return "此数据集存储在仅限单个用户访问的存储空间中。它不能被共享、发布或添加到Galaxy数据库中。";
    } else {
        return "此数据集存储在允许标准Galaxy共享功能的存储空间中。如果您对此数据集有足够的Galaxy权限，该数据集可以在Galaxy内被发布、共享或添加到数据库。";
    }
});
</script>

<template>
    <span v-b-tooltip.hover class="stored-how object-store-help-on-hover" :title="title">{{ text }}</span>
</template>

<style scoped>
@import "./style.css";
</style>
