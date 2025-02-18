<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BRow } from "bootstrap-vue";
import { faGear, type IconDefinition } from "font-awesome-6";
import type { PropType } from "vue";

const props = defineProps({
    id: {
        type: String,
        default: null,
    },
    icon: {
        type: Object as PropType<IconDefinition>,
        default: () => faGear,
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

const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <BRow class="ml-3 mb-1">
        <FontAwesomeIcon :icon="props.icon" size="lg" class="pt-1 pref-icon" />
        <div class="pref-content pr-1">
            <b-badge v-if="Boolean(props.badge)" variant="danger">
                {{ props.badge }}
            </b-badge>
            <router-link v-if="to" :id="props.id" :to="props.to">
                <b v-localize>{{ props.title }}</b>
            </router-link>
            <a v-else :id="props.id" href="#" @click="emit('click')">
                <b v-localize>{{ props.title }}</b>
            </a>
            <div class="form-text text-muted">
                {{ props.description }}
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
