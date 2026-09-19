<script setup lang="ts">
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>
<template>
    <q-icon name="format_quote" color="primary" :size="size" />
    <div :class="classes">
        <div class="text-subtitle1 text-weight-bold">Cite</div>
        <div class="text-body1">
            Information on citing the tool shed can be found on the Galaxy Hub
            <a href="https://galaxyproject.org/citing-galaxy/#toolshed">here</a>.
        </div>
    </div>
</template>
