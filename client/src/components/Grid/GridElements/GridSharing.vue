<script setup lang="ts">
import { computed } from "vue";

interface Props {
    published: Boolean;
    importable: Boolean;
    users_shared_with_length: number;
}

const props = defineProps<Props>();

/**
 * Check if item has been shared
 */
const isShared = computed(() => {
    return props.published || props.importable || props.users_shared_with_length;
});

/**
 * Generate title containing the number of users with access to the item
 */
const sharedTitle = computed(() => {
    const title = `Shared with ${props.users_shared_with_length}`;
    return props.users_shared_with_length > 1 ? `${title} users` : `${title} user`;
});
</script>

<template>
    <span>
        <span v-if="isShared">
            <span v-if="props.published" v-b-tooltip.hover title="Published" class="mr-1">
                <icon icon="globe" />
            </span>
            <span v-if="props.importable" v-b-tooltip.hover title="Accessible by link" class="mr-1">
                <icon icon="link" />
            </span>
            <span v-if="props.users_shared_with_length" v-b-tooltip.hover :title="sharedTitle" class="mr-1">
                <icon icon="users" />
            </span>
        </span>
        <span v-else v-b-tooltip.hover title="Not shared">
            <icon icon="lock" />
        </span>
    </span>
</template>
