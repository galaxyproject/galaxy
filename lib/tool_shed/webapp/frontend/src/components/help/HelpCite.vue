<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faQuoteLeft } from "@fortawesome/free-solid-svg-icons"
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>
<template>
    <FontAwesomeIcon :icon="faQuoteLeft" class="text-primary" :style="{ fontSize: size }" />
    <div :class="classes">
        <div class="text-subtitle1 text-weight-bold">Cite</div>
        <div class="text-body1">
            Information on citing the tool shed can be found on the Galaxy Hub
            <a href="https://galaxyproject.org/citing-galaxy/#toolshed">here</a>.
        </div>
    </div>
</template>
