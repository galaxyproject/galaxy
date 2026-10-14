<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faQuoteLeft } from "@fortawesome/free-solid-svg-icons"
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>
<template>
    <FontAwesomeIcon :icon="faQuoteLeft" class="help-icon" :style="{ fontSize: size }" />
    <div :class="classes">
        <h2 class="help-heading">Cite</h2>
        <div>
            Information on citing the tool shed can be found on the Galaxy Hub
            <a href="https://galaxyproject.org/citing-galaxy/#toolshed">here</a>.
        </div>
    </div>
</template>

<style scoped>
.help-icon {
    color: var(--color-galaxy-primary);
}

.help-heading {
    margin: 0;
    font-size: 1rem;
    font-weight: bold;
}

.help-align-left,
.help-align-center {
    margin-top: var(--spacing-4);
    /* Quasar's text-body1, which this text carried */
    font-size: 1rem;
    line-height: 1.5;
}

.help-align-left {
    text-align: left;
    padding-bottom: calc(var(--spacing-8) + var(--spacing-4));
}

.help-align-center {
    text-align: center;
}
</style>
