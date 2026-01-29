<script setup lang="ts">
import { computed } from "vue";

import { useFileSources } from "@/composables/fileSources";

interface Props {
    uri: string;
    showFullUri?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    showFullUri: false,
});

const { getFileSourceByUri } = useFileSources();

const fileSource = computed(() => getFileSourceByUri(props.uri));

const fileSourceName = computed(() => fileSource.value?.label ?? fileSource.value?.id);
</script>

<template>
    <span>
        {{ fileSourceName }} <span v-if="showFullUri">➡️ {{ props.uri }}</span>
    </span>
</template>
