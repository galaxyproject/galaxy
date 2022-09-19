<template>
    <div>
        <header class="main-header">
            <h1 class="text-center my-3">{{ title | localize }}</h1>
            <h4 class="text-center my-3">{{ intro | localize }}</h4>
        </header>
        <b-row class="justify-content-md-center mb-3">
            <b-card-group v-for="(subject, idx) in topics" :key="idx">
                <b-card class="text-center m-2 border-0" body-class="d-flex flex-column">
                    <b-card-img
                        class="section-header mb-3"
                        height="50h"
                        :src="imgUrl(subject.image)"
                        :alt="subject.alt"></b-card-img>
                    <b-card-text class="font-weight-light">{{ subject.blurb | localize }}</b-card-text>
                    <b-button class="mt-auto" variant="info" @click="$emit('select', idx)">{{
                        subject.title | localize
                    }}</b-button>
                </b-card>
            </b-card-group>
        </b-row>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
export default {
    props: {
        topics: {
            type: Array,
            required: true,
        },
        imageLoc: {
            type: String,
            required: false,
            default: "plugins/welcome_page/new_user/dist/static/topics/",
        },
        title: {
            type: String,
            default: "Welcome to Galaxy",
        },
        intro: {
            type: String,
            default:
                "Galaxy is web-based platform for reproducible computational analysis. Research in Galaxy \
                is supported by 3 pillars: data, tools, and workflows. For an introduction to each, visit the \
                below pages, or begin your analysis by selting a tool from the toolbar to the left.",
        },
    },
    methods: {
        imgUrl(src) {
            const root = getAppRoot();
            const url = `${root}static/${this.imageLoc}${src}`.replace("//", "/");
            return url;
        },
    },
};
</script>
<style scoped>
.card {
    width: 15rem;
}
</style>
