<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLongArrowAltLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import Heading from "@/components/Common/Heading.vue";

library.add(faLongArrowAltLeft);

const props = defineProps<{
    heading: string;
    icon: string;
    backLinkUrl?: string;
    backLinkText?: string;
}>();

const backUrl = computed(() => props.backLinkUrl ?? "/user");
const backText = computed(() => props.backLinkText ?? "back to preferences");
</script>

<template>
    <section class="preferences-page">
        <BButton :to="backUrl" class="back-button" size="sm" variant="primary">
            <FontAwesomeIcon icon="fa-long-arrow-alt-left" />
            {{ backText }}
        </BButton>

        <Heading h1 inline separator :icon="props.icon">
            {{ props.heading }}
        </Heading>

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
}
</style>
