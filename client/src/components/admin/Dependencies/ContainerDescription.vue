<template>
    <span class="container-description">
        <span v-if="containerDescription" :title="title">
            <a v-if="externalUrl" class="icon-btn" :href="externalUrl"><span class="fa fa-link"></span></a>
            {{ containerDescription.identifier }}
            <span v-if="!compact">
                <i>{{ description }}</i>
                <DisplayRaw :object="containerDescription" />
            </span>
        </span>
        <span v-else>
            <i>no container resolved</i>
        </span>
    </span>
</template>
<script>
import DisplayRaw from "./DisplayRaw";

export default {
    components: { DisplayRaw },
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
            return `这是一个 ${this.containerDescription.type} 容器。${this.shellDescription}`;
        },
        shellDescription: function () {
            return `该容器使用 [${this.containerDescription.shell}] shell.`;
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
