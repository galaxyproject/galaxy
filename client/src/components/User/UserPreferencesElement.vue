<script setup>
import { BRow } from "bootstrap-vue";
defineProps({
    id: {
        type: String,
        default: null,
    },
    icon: {
        type: String,
        default: "fa-gear",
    },
    title: {
        type: String,
        default: "Title not available.",
    },
    description: {
        type: String,
        default: "Description not available.",
    },
    to: {
        type: String,
        default: null,
    },
    badge: {
        type: String,
        default: null,
    },
});
</script>
<template>
    <b-row class="ml-3 mb-1">
        <i :class="['pref-icon pt-1 fa fa-lg', icon]" />
        <div class="pref-content pr-1">
            <b-badge v-if="!!badge" variant="danger">
                {{ badge }}
            </b-badge>
            <router-link v-if="to" :id="id" :to="to">
                <b v-localize>{{ title }}</b>
            </router-link>
            <a v-else :id="id" href="#" @click="$emit('click')">
                <b v-localize>{{ title }}</b>
            </a>
            <div class="form-text text-muted">
                {{ description }}
            </div>
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
