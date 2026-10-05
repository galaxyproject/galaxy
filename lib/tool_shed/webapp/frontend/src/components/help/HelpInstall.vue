<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faDownload } from "@fortawesome/free-solid-svg-icons"
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>

<template>
    <FontAwesomeIcon :icon="faDownload" class="help-icon" :style="{ fontSize: size }" />
    <div :class="classes">
        <h3 class="help-heading">Installing</h3>
        <div>
            There best, most updated resource for information on installing tools in Galaxy from the tool shed can be
            found in tutorial
            <a
                href="https://training.galaxyproject.org/training-material/topics/admin/tutorials/tool-management/tutorial.html"
                >Galaxy Tool Management with Ephemeris</a
            >
            maintained by the Galaxy Training Network (GTN).
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
