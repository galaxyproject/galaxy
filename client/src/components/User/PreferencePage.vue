<script setup lang="ts">
import { faLongArrowAltLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    heading: string;
    icon: any;
    description?: string;
    backLinkUrl?: string;
    backLinkText?: string;
}>();

const backUrl = computed(() => props.backLinkUrl ?? "/user");
const backText = computed(() => props.backLinkText ?? "back to preferences");
</script>

<template>
    <section class="preferences-page">
        <BButton :to="backUrl" class="back-button" size="sm" variant="primary">
            <FontAwesomeIcon :icon="faLongArrowAltLeft" />
            {{ backText }}
        </BButton>

        <Heading h1 inline separator :icon="props.icon">
            {{ props.heading }}
        </Heading>

        <p v-if="props.description">
            {{ props.description }}
        </p>

        <slot></slot>
    </section>
</template>

<style scoped lang="scss">
.preferences-page {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;

    .back-button {
        align-self: self-start;
    }

    p {
        margin: 0;
    }
}
</style>
