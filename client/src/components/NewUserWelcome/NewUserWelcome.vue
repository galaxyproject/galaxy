<template>
    <div class="new-user-welcome">
        <ConfigProvider v-slot="config">
            <component
                :is="viewElement"
                v-if="loaded === true"
                v-bind="currentNode"
                :image-loc="config.welcome_directory"
                @select="down"
                @back="up">
            </component>
            <div v-else-if="loaded === false">
                <!--
                    this shouldn't ever show unless the load actually fails,
                    which shouldn't happen -- just a barebones failsafe 
                -->
                <Heading h1>Welcome to Galaxy!</Heading>
                <p>
                    Galaxy is web-based platform for reproducible computational analysis. Research in Galaxy is
                    supported by 3 pillars: data, tools, and workflows.
                </p>
                <p>
                    If this is your first time using Galaxy we strongly recommend looking at the introductory materials
                    available at <a href="https://training.galaxyproject.org">training.galaxyproject.org</a>.
                </p>
            </div>
        </ConfigProvider>
    </div>
</template>
<script>
import { BCard, BCardGroup, BTabs, BTab, BCarousel, BCarouselSlide, BButton, BRow, BCol } from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { getResource } from "./getResource";
import Topics from "components/NewUserWelcome/components/Topics";
import Subtopics from "components/NewUserWelcome/components/Subtopics";
import Slides from "components/NewUserWelcome/components/Slides";
import ConfigProvider from "components/providers/ConfigProvider";
import Heading from "components/Common/Heading";

export default {
    components: {
        Heading,
        BCard,
        BCardGroup,
        BTabs,
        BTab,
        BCarousel,
        BCarouselSlide,
        BButton,
        BRow,
        BCol,
        Topics,
        Subtopics,
        Slides,
        ConfigProvider,
    },
    data() {
        return {
            loaded: undefined,
            position: [],
            newUser: {},
        };
    },
    computed: {
        depth() {
            return this.position.length;
        },
        currentNode() {
            const userDict = this.newUser;
            return this.position.reduce((node, i) => {
                return node.topics[i];
            }, userDict);
        },
        viewElement() {
            let element;
            switch (this.depth) {
                case 0:
                    element = Topics;
                    break;
                case 1:
                    element = Subtopics;
                    break;
                case 2:
                    element = Slides;
                    break;
            }
            return element;
        },
    },
    async mounted() {
        // todo, move to config, use non-webpack import and load like a plugin
        const resource = await getResource();
        if (resource?.newUserDict) {
            this.newUser = resource.newUserDict;
            this.loaded = true;
        } else {
            // Custom contents in component if this happens to fail, redirecting to tours or something?
        }
    },
    methods: {
        imgUrl(src) {
            const root = getAppRoot();
            const url = `${root}static/${this.imageLoc}${src}`.replace("//", "/");
            return url;
        },
        up() {
            this.position.pop();
        },
        down(index) {
            this.position.push(index);
        },
    },
};
</script>

<style scoped type="scss">
.new-user-welcome:deep() {
    .carousel-fig {
        padding-bottom: 10;
    }
    .carousel-caption {
        position: relative;
        left: 0;
        top: 0;
        color: black;
        padding-bottom: 10;
        padding-left: 1vw;
        padding-right: 1vw;
    }
    .carousel-item {
        float: none;
        margin-right: auto;
        margin-left: auto;
    }
    .carousel-indicators {
        position: sticky;
        bottom: 30px;
    }
    .button-housing {
        position: sticky;
        z-index: 21;
        padding-right: 67.88px;
    }
    .carousel-button {
        position: fixed;
        z-index: 20;
        bottom: 10px;
    }
    .carousel-control-next,
    .carousel-control-prev,
    .carousel-indicators {
        filter: invert(100%);
    }
    .carousel-control-next,
    .carousel-control-prev {
        border-left: 1px;
        border-right: 1px;
        z-index: 11;
        align-items: center;
        justify-content: center;
        height: fit-content;
        height: 85vh;
        width: 2vw;
    }
    .carousel-control-next:hover,
    .carousel-control-prev:hover {
        background-color: grey;
    }
    #logos img {
        max-width: 100%;
    }
    .carousel-inner {
        position: absolute;
    }
    .mini-img {
        max-width: 100px;
    }
    .small-img {
        max-width: 300px;
    }
    .med-img {
        max-width: 500px;
    }
    .large-img {
        max-width: 700px;
    }
    .slide-header {
        text-align: center;
        padding-bottom: 3;
    }
    .section-header {
        filter: invert(16%) sepia(14%) saturate(1113%) hue-rotate(189deg) brightness(99%) contrast(91%);
    }
}
</style>
