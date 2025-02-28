<script setup lang="ts">
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>

<template>
    <q-icon name="search" color="primary" :size="size" />
    <div :class="classes">
        <div class="text-subtitle1 text-weight-bold">Explore</div>
        <div class="text-body1">
            Click the explore menu at the top right of the page to start exploring the tools in the Galaxy Tool Shed or
            to search for the repository you're looking for.
        </div>
    </div>
</template>
