<script setup lang="ts">
import { RouterLink } from "vue-router";

import { type BreadcrumbItem } from "@/components/Common/index";
import localize from "@/utils/localization";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    items: BreadcrumbItem[];
}

const props = defineProps<Props>();
</script>

<template>
    <div class="breadcrumb-heading">
        <Heading h1 separator inline size="xl" class="breadcrumb-heading-header">
            <template v-for="(item, index) in props.items">
                <RouterLink v-if="item.to" :key="index" :to="item.to">
                    {{ localize(item.title) }}
                </RouterLink>
                <span v-else :key="'else-' + index">
                    {{ localize(item.title) }}
                </span>

                <template v-if="item.superText">
                    <sup :key="'sup-' + index" class="breadcrumb-heading-header-beta">
                        {{ localize(item.superText) }}
                    </sup>
                </template>

                <template v-if="index < items.length - 1"> / </template>
            </template>
        </Heading>

        <slot />
    </div>
</template>

<style scoped lang="scss">
.breadcrumb-heading {
    display: flex;

    .breadcrumb-heading-header {
        flex-grow: 1;
        margin-bottom: 0.5rem;

        .breadcrumb-heading-header-beta {
            color: #717273;
        }
    }
}
</style>
