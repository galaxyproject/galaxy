<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BRow } from "bootstrap-vue";

import type { IconLike } from "@/components/icons/galaxyIcons";

defineProps<{
    id?: string;
    icon: IconLike;
    title?: string;
    description?: string;
    to?: string;
    badge?: string;
}>();
</script>
<template>
    <BRow class="ml-3 mb-1">
        <FontAwesomeIcon fixed-width size="lg" class="pref-icon pt-1" :icon="icon" />
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
    </BRow>
</template>
<style scoped>
.pref-content {
    width: calc(100% - 3rem);
}
.pref-icon {
    width: 3rem;
}
</style>
