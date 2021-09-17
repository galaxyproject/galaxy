<template>
    <div>
        <b-card class="text-center">
            <b-card-header>
                <h1>{{ title | localize }}</h1>
                <h4>
                    {{ intro | localize }}
                </h4>
            </b-card-header>
            <b-row class="justify-content-md-center">
                <b-card-group style="d-flex flex-column" v-for="(subject, idx) in topics" :key="idx">
                    <b-card class="text-center" body-class="d-flex flex-column" style="width: 15rem">
                        <b-card-header style="height: 6rem; text-align: center; align-v: bottom">
                            <h4>
                                {{ subject.title | localize }}
                            </h4>
                        </b-card-header>
                        <b-card-img
                            class="section-header"
                            height="200vh"
                            :src="imgUrl(subject.image)"
                            :alt="subject.alt"
                        ></b-card-img>
                        <b-card-text>{{ subject.intro | localize }}</b-card-text>
                        <b-button class="mt-auto" variant="primary" @click="$emit('select', idx)">Learn more</b-button>
                    </b-card>
                </b-card-group>
            </b-row>
            <b-card-footer>
                <b-button class="mt-auto" variant="primary" @click="$emit('back')">Return</b-button>
            </b-card-footer>
        </b-card>
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
