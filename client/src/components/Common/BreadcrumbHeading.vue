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
    <div class="breadcrumb-heading mb-2">
        <Heading h1 separator inline size="md" class="breadcrumb-heading-header mr-2 mb-0">
            <template v-for="(item, index) in props.items">
                <RouterLink
                    v-if="item.to"
                    :key="index"
                    v-b-tooltip.hover.bottom.noninteractive
                    :title="`Go back to ${localize(item.title)}`"
                    :to="item.to"
                    class="breadcrumb-heading-header-active">
                    {{ localize(item.title) }}
                </RouterLink>
                <span v-else :key="'else-' + index" class="breadcrumb-heading-header-inactive">
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

        .breadcrumb-heading-header-active {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;

            &:hover {
                cursor: pointer;
            }
        }

        .breadcrumb-heading-header-inactive {
            flex-shrink: 0;
            margin-left: auto;
        }

        .breadcrumb-heading-header-beta {
            color: #717273;
        }
    }
}
</style>
