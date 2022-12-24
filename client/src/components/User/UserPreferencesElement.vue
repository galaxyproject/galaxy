<script setup>
import { BRow } from "bootstrap-vue";
const props = defineProps({
    icon: {
        type: String,
        default: "fa-gear",
    },
});
</script>
<template>
    <b-row class="ml-3 mb-1">
        <i :class="['pref-icon pt-1 fa fa-lg', icon]" />
        <div class="pref-content pr-1">
            <slot />
        </div>
    </b-row>
</template>
<style scoped>
.pref-content {
    width: calc(100% - 3rem);
}
.pref-icon {
    width: 3rem;
}
</style>
