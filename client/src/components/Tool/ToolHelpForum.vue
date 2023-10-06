<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";
</script>

<template>
    <div class="tool-help-forum">
        <Heading h2 separator bold size="sm">Help Forum</Heading>

        <p>
            There are no questions on the
            <ExternalLink href="help forum link here"> Help Forum </ExternalLink>
            about this tool.
        </p>

        <BButton variant="primary" class="font-weight-bold" target="blank" href="help forum new question link here">
            <FontAwesomeIcon :icon="['gxd', 'galaxyLogo']" /> Ask a new question
        </BButton>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.tool-help-forum {
    --fa-secondary-color: #{$brand-toggle};
    --fa-secondary-opacity: 1;
}
</style>
