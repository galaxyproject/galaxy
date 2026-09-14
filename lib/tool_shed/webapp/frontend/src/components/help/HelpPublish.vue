<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faUpload } from "@fortawesome/free-solid-svg-icons"
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>

<template>
    <FontAwesomeIcon :icon="faUpload" class="text-primary" :style="{ fontSize: size }" />
    <div :class="classes">
        <div class="text-subtitle1 text-weight-bold">Publish</div>
        <div class="text-body1">
            There best, most updated resource for information on publishing tools to the tool shed is the tutorial
            <a href="https://planemo.readthedocs.io/en/latest/publishing.html">Publishing to the Tool Shed</a>. This
            tutorial is part of the Planemo Docs - which contain a lot more information on developing and testing Galaxy
            tools.
        </div>
    </div>
</template>
