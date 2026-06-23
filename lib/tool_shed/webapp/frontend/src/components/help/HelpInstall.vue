<script setup lang="ts">
import { CommonProps, useCommonProps } from "./_util"

const props = defineProps<CommonProps>()
const { classes, size } = useCommonProps(props)
</script>

<template>
    <q-icon name="download" color="primary" :size="size" />
    <div :class="classes">
        <div class="text-subtitle1 text-weight-bold">Installing</div>
        <div class="text-body1">
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
