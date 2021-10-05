<template>
    <div class="user-welcome-topics">
        <header class="main-header alert alert-info">
            <h1 class="text-center my-3">{{ "Welcome to Galaxy" | localize }}</h1>
            <span>
                {{
                    "Galaxy is web-based platform for reproducible computational analysis. Research in Galaxy \
                is supported by 3 pillars: data, tools, and workflows. For an introduction to each, visit the \
                below pages, or begin your analysis by selting a tool from the toolbar to the left."
                        | localize
                }}
            </span>
        </header>
        <b-row class="justify-content-md-center">
            <b-card-group v-for="(subject, idx) in topics" :key="idx">
                <b-card class="text-center border-0" body-class="d-flex flex-column">
                    <b-card-img
                        class="section-header mb-3"
                        height="50h"
                        :src="imgUrl(subject.image)"
                        :alt="subject.alt"
                    ></b-card-img>
                    <b-card-text>{{ subject.blurb | localize }}</b-card-text>
                    <b-button class="mt-auto" variant="primary" @click="$emit('select', idx)">{{ subject.title | localize }}</b-button>
                </b-card>
            </b-card-group>
        </b-row>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
export default {
    props: {
        topics: { type: Array, required: true },
        imageLoc: { type: String, required: false, default: "plugins/welcome_page/new_user/dist/static/topics/" },
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
