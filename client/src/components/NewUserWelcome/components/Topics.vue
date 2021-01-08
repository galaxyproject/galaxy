<template>
    <div>
        <header class="main-header text-center">
            <h1>{{ "Welcome to Galaxy" | localize }}</h1> 
            <span>
                {{ "Galaxy is web-based platform for reproducible computational analysis. Research in Galaxy \
                is supported by 3 pillars: data, tools, and workflows. For an introduction to each, visit the \
                below pages, or begin your analysis by selting a tool from the toolbar to the left." | localize }} 
            </span>
        </header>
        <b-card class="text-center">
            <b-card-header>
            <h1>{{ "Get to Know Galaxy" | localize }}</h1>
            </b-card-header>
            <b-row class="justify-content-md-center">
                <b-card-group v-for="(subject, idx) in topics" :key="idx">
                    <b-card class="text-center" body-class="d-flex flex-column" style="width: 18rem;">
                            <b-card-header class="text-center"> 
                                <h3>
                                    {{ subject.title | localize }}
                                </h3>
                            </b-card-header>
                        <b-card-img class="section-header" height="200vh" :src="imgUrl(subject.image)" :alt="subject.alt"></b-card-img>
                        <b-card-text>{{ subject.blurb | localize }}</b-card-text>
                        <b-button class="mt-auto" variant="primary" @click="$emit('select', idx)">Learn more</b-button>
                    </b-card>
                </b-card-group>
            </b-row>
        </b-card>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
export default {

    props: {
        topics: {type: Array, required: true},
        imageLoc: {type: String, required: false, default: "static/plugins/welcome_page/new_user/static/topics/"},
    },
    methods:    {    
        imgUrl(src) {
            const root = getAppRoot();
            const url = `${root}${this.imageLoc}${src}`.replace("//", "/");
            return url;
        }
    }
};
</script>