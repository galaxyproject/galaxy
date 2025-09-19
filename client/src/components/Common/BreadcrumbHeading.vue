<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import type { RawLocation } from "vue-router";
import { useRouter } from "vue-router/composables";

import type { BreadcrumbItem } from "@/components/Common/index";
import localize from "@/utils/localization";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    /** Array of items to display in the breadcrumb */
    items: BreadcrumbItem[];
}

const props = defineProps<Props>();

const router = useRouter();

function isPathActive(path: RawLocation): boolean {
    return router.currentRoute.path === router.resolve(path).route.path;
}
</script>

<template>
    <div class="breadcrumb-heading mb-2">
        <Heading h1 separator inline size="lg" class="breadcrumb-heading-header mr-2 mb-0">
            <template v-for="(item, index) in props.items">
                <BLink
                    v-if="item.to && !isPathActive(item.to)"
                    :key="index"
                    v-b-tooltip.hover.bottom.noninteractive
                    :title="`Go back to ${localize(item.title)}`"
                    :to="item.to"
                    class="breadcrumb-heading-header-active">
                    <FontAwesomeIcon v-if="item.icon" :icon="item.icon" />
                    {{ localize(item.title) }}
                </BLink>
                <span v-else :key="'else-' + index" class="breadcrumb-heading-header-inactive">
                    <FontAwesomeIcon v-if="item.icon" :icon="item.icon" />
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
