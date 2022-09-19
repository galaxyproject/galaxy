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
                    <b-card-text class="font-weight-light">{{ subject.intro | localize }}</b-card-text>
                    <b-button class="mt-auto" variant="info" @click="$emit('select', idx)">{{
                        subject.title | localize
                    }}</b-button>
                </b-card>
            </b-card-group>
        </b-row>
        <b-button class="mt-auto" variant="primary" role="link" @click="$emit('back')">
            <span class="fa fa-caret-left mr-1" />
            <span>Return</span>
        </b-button>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
export default {
    props: {
        topics: { type: Array, required: true },
        title: { type: String, required: true },
        image: { type: String, required: true },
        blurb: { type: String, required: true },
        intro: { type: String, required: true },
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
<style scoped>
.card {
    width: 15rem;
}
</style>
