<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faUpload } from "@fortawesome/free-solid-svg-icons"
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>

<template>
    <FontAwesomeIcon :icon="faUpload" class="help-icon" :style="{ fontSize: size }" />
    <div :class="classes">
        <h3 class="help-heading">Publish</h3>
        <div>
            There best, most updated resource for information on publishing tools to the tool shed is the tutorial
            <a href="https://planemo.readthedocs.io/en/latest/publishing.html">Publishing to the Tool Shed</a>. This
            tutorial is part of the Planemo Docs - which contain a lot more information on developing and testing Galaxy
            tools.
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
