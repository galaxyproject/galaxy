<script setup lang="ts">
import { faWrench, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";

import { absPath } from "@/utils/redirect";

import Heading from "@/components/Common/Heading.vue";

withDefaults(
    defineProps<{
        errorMessage: string;
        description?: string;
        isLoading?: boolean;
        icon?: IconDefinition;
        logo?: string;
        name?: string;
        version?: string;
    }>(),
    {
        isLoading: false,
    }
);
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    <LoadingSpan v-else-if="isLoading" />
    <div v-else>
        <div class="position-relative">
            <div class="ui-form-header-underlay sticky-top" />
            <div class="tool-header sticky-top bg-secondary px-2 py-1 rounded">
                <div class="d-flex justify-content-between">
                    <div class="py-1 d-flex flex-wrap flex-gapx-1 align-items-center">
                        <img v-if="logo" class="fa-fw" alt="logo" :src="absPath(logo)" />
                        <FontAwesomeIcon v-else :icon="icon || faWrench" class="fa-fw" />
                        <Heading h1 inline bold size="text" itemprop="name">{{ name }}</Heading>
                        <span itemprop="description">{{ description }}</span>
                        <span v-if="version" class="text-muted">(Galaxy Version {{ version }})</span>
                    </div>
                    <div class="d-flex flex-nowrap align-items-start flex-gapx-1">
                        <slot name="buttons" />
                    </div>
                </div>
            </div>
            <div id="tool-card-body">
                <slot name="default" />
            </div>
            <slot name="footer" />
        </div>
    </div>
</template>
