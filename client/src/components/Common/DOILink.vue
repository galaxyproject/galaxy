<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

library.add(faLink);

interface Props {
    doi: string;
}

const props = defineProps<Props>();

const doiLink = computed(() => `https://doi.org/${props.doi}`);
</script>

<template>
    <BBadge class="doi-badge">
        <FontAwesomeIcon :icon="faLink" />
        <a :href="doiLink" target="_blank" rel="noopener noreferrer">{{ props.doi }}</a>
    </BBadge>
</template>

<style scoped>
.doi-badge {
    font-size: 1rem;
}
</style>
