<template>
    <span class="page-url-entry">
        <span>u/</span><a href="#" class="page-url-owner" @click.prevent="onClickOwner">{{ owner }}</a
        ><span>/p/{{ slug }}</span>
        <font-awesome-icon
            v-b-tooltip.hover
            :title="linkTitle | localize"
            class="page-url-copy"
            icon="copy"
            style="cursor: pointer"
            @click="copyLink" />
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { copy } from "utils/clipboard";

library.add(faCopy);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        root: {
            type: String,
            required: true,
        },
        owner: {
            type: String,
            required: true,
        },
        slug: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            linkTitle: "Copy URL Link to Galaxy Page",
        };
    },
    methods: {
        onClickOwner() {
            this.$emit("click-owner", this.owner);
        },
        copyLink() {
            copy(`${this.root}/u/${this.owner}/p/${this.slug}`);
        },
    },
};
</script>
