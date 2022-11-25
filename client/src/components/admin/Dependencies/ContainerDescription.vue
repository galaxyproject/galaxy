<template>
    <span class="container-description">
        <span v-if="containerDescription" :title="title">
            <a v-if="externalUrl" class="icon-btn" :href="externalUrl"
                ><FontAwesomeIcon icon="fa-link"></FontAwesomeIcon
            ></a>
            {{ containerDescription.identifier }}
            <span v-if="!compact">
                <i>{{ description }}</i>
                <display-raw :object="containerDescription" />
            </span>
        </span>
        <span v-else>
            <i>no container resolved</i>
        </span>
    </span>
</template>
<script>
import DisplayRaw from "./DisplayRaw";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLink } from "@fortawesome/free-solid-svg-icons";

library.add(faLink);

export default {
    components: { DisplayRaw, FontAwesomeIcon },
    props: {
        containerDescription: {
            type: Object,
        },
        compact: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        title: function () {
            return this.compact ? this.description : "";
        },
        description: function () {
            return `This is a ${this.containerDescription.type} container. ${this.shellDescription}`;
        },
        shellDescription: function () {
            return `This container uses shell [${this.containerDescription.shell}].`;
        },
        identifier: function () {
            return this.containerDescription && this.containerDescription.identifier;
        },
        externalUrl: function () {
            const identifier = this.identifier;
            if (identifier) {
                if (identifier.startsWith("quay.io")) {
                    return "http://" + identifier;
                }
            }
            return null;
        },
    },
};
</script>
