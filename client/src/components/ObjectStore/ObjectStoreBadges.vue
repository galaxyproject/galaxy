<script lang="ts" setup>
import ObjectStoreBadge from "./ObjectStoreBadge.vue";
import type { components } from "@/schema";
type BadgeType = components["schemas"]["BadgeDict"];

interface ObjectStoreBadgesProps {
    badges: Array<BadgeType>;
    size?: string;
    moreOnHover?: boolean;
}

withDefaults(defineProps<ObjectStoreBadgesProps>(), {
    size: "3x",
    moreOnHover: true,
});
</script>

<template>
    <div class="object-store-badges">
        <ObjectStoreBadge
            v-for="(badge, idx) in badges"
            :key="idx"
            :badge="badge"
            :size="size"
            :more-on-hover="moreOnHover">
        </ObjectStoreBadge>
    </div>
</template>
