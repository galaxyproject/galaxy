<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { RouteLocationRaw } from "vue-router";
import { useRoute, useRouter } from "vue-router";

import type { BreadcrumbItem } from "@/components/Common/index";
import localize from "@/utils/localization";

import GLink from "@/components/BaseComponents/GLink.vue";
import Heading from "@/components/Common/Heading.vue";

interface Props {
    /** Array of items to display in the breadcrumb */
    items: BreadcrumbItem[];
}

const props = defineProps<Props>();

const router = useRouter();
const route = useRoute();

function isPathActive(path: RouteLocationRaw): boolean {
    return route.path === router.resolve(path).path;
}

// GLink takes a path string, while items may pass a named route location
function resolvePath(path: RouteLocationRaw): string {
    return typeof path === "string" ? path : router.resolve(path).fullPath;
}
</script>

<template>
    <div class="breadcrumb-heading mb-2">
        <Heading h1 separator inline size="lg" class="breadcrumb-heading-header mr-2 mb-0">
            <template v-for="(item, index) in props.items" :key="index">
                <GLink
                    v-if="item.to && !isPathActive(item.to)"
                    v-g-tooltip.hover.bottom
                    class="breadcrumb-heading-header-active"
                    :title="`Go back to ${localize(item.title)}`"
                    :to="resolvePath(item.to)">
                    <FontAwesomeIcon v-if="item.icon" :icon="item.icon" />
                    {{ localize(item.title) }}
                </GLink>
                <span v-else class="breadcrumb-heading-header-inactive">
                    <FontAwesomeIcon v-if="item.icon" :icon="item.icon" />
                    {{ localize(item.title) }}
                </span>

                <template v-if="item.superText">
                    <sup :key="'sup-' + index" class="breadcrumb-heading-header-beta">
                        {{ localize(item.superText) }}
                    </sup>
                </template>

                <span v-if="index < items.length - 1" :key="'sep-' + index" class="breadcrumb-separator"> / </span>
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
        min-width: 0;

        :deep(.separator) {
            grid-template-columns: 1rem 1fr 1rem;
        }

        :deep(h1) {
            overflow: hidden;
        }

        .breadcrumb-heading-header-active {
            // Same weight as the inactive crumbs and the heading around them
            font-weight: inherit;
            min-width: 0;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            flex-shrink: 1;

            &:hover {
                cursor: pointer;
            }
        }

        .breadcrumb-heading-header-inactive {
            white-space: nowrap;
            flex-shrink: 0;
        }

        .breadcrumb-separator {
            flex-shrink: 0;
        }

        .breadcrumb-heading-header-beta {
            color: var(--color-grey-500);
            white-space: nowrap;
            flex-shrink: 0;
        }
    }
}
</style>
