<template>
    <span class="page-url-entry">
        <span>u/</span><a href="#" class="page-url-owner" @click.prevent="onClickOwner">{{ owner }}</a
        ><span>/p/{{ slug }}</span>
        <span v-b-tooltip.hover class="page-url-copy" :title="linkTitle | localize"
            ><font-awesome-icon icon="copy" style="cursor: pointer" @click="copyLink"
        /></span>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { copy } from "utils/clipboard";
import { absPath } from "@/utils/redirect";
import _l from "utils/localization";

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
            copy(absPath(`/u/${this.owner}/p/${this.slug}`), _l("Link copied to your clipboard"));
        },
    },
};
</script>
