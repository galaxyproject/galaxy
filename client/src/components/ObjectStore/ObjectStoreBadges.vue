<template>
    <div class="object-store-badges">
        <ObjectStoreBadge
            v-for="(badge, idx) in badges"
            :key="idx"
            :badge="badge"
            :size="size"
            :moreOnHover="moreOnHover">
        </ObjectStoreBadge>
    </div>
</template>

<script>
import ObjectStoreBadge from "./ObjectStoreBadge";

export default {
    components: {
        ObjectStoreBadge,
    },
    props: {
        badges: {
            type: Array,
            required: true,
        },
        size: {
            type: String,
            default: "3x",
        },
        moreOnHover: {
            type: Boolean,
            default: true,
        },
    },
};
</script>
