<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { IconDefinition } from "font-awesome-6";

const props = defineProps<{
    icon?: IconDefinition;
    title?: string;
}>();
</script>

<template>
    <div class="ui-portlet-section">
        <div class="portlet-header">
            <span class="portlet-title">
                <FontAwesomeIcon v-if="props.icon" :icon="props.icon" class="portlet-title-icon mr-1" />

                <b class="portlet-title-text">
                    <slot name="title">
                        {{ props.title }}
                    </slot>
                </b>
            </span>
        </div>

        <div class="portlet-content">
            <div class="mt-3">
                <slot />
            </div>
        </div>
    </div>
</template>
