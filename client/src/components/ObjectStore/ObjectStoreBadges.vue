<script setup lang="ts">
import { type components } from "@/api/schema";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";

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
