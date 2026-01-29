<script setup lang="ts">
import { computed, ref } from "vue"

import HelpSearch from "@/components/help/HelpSearch.vue"
import HelpInstall from "@/components/help/HelpInstall.vue"
import HelpPublish from "@/components/help/HelpPublish.vue"
import HelpCite from "@/components/help/HelpCite.vue"

const slide = ref("install")

const commonProps = computed(() => {
    return { hAlign: "center" as "left" | "center" }
})
</script>

<template>
    <q-carousel
        v-model="slide"
        infinite
        transition-prev="slide-right"
        transition-next="slide-left"
        animated
        :autoplay="true"
        navigation
        control-color="primary"
        class="rounded-borders"
    >
        <q-carousel-slide name="find" class="column no-wrap flex-center">
            <HelpSearch v-bind="commonProps" />
        </q-carousel-slide>
        <q-carousel-slide name="install" class="column no-wrap flex-center">
            <HelpInstall v-bind="commonProps" />
        </q-carousel-slide>
        <q-carousel-slide name="publish" class="column no-wrap flex-center">
            <HelpPublish v-bind="commonProps" />
        </q-carousel-slide>
        <q-carousel-slide name="cite" class="column no-wrap flex-center">
            <HelpCite v-bind="commonProps" />
        </q-carousel-slide>
    </q-carousel>
</template>
