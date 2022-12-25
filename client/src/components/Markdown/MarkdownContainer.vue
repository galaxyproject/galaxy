<template>
    <div>
        <b-link v-if="isCollapsible" class="font-weight-bold" @click="toggle = !toggle">
            {{ obj.args.collapse }}
        </b-link>
        <b-collapse :visible="isVisible">
            <markdown-element
                :obj="obj"
                :datasets="datasets"
                :collections="collections"
                :histories="histories"
                :invocations="invocations"
                :jobs="jobs"
                :workflows="workflows" />
        </b-collapse>
    </div>
</template>

<script>
import MarkdownElement from "./MarkdownElement.vue";
export default {
    components: {
        MarkdownElement,
    },
    props: {
        obj: {
            type: Object,
            default: null,
        },
        datasets: {
            type: Object,
            default: null,
        },
        collections: {
            type: Object,
            default: null,
        },
        histories: {
            type: Object,
            default: null,
        },
        invocations: {
            type: Object,
            default: null,
        },
        jobs: {
            type: Object,
            default: null,
        },
        workflows: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            toggle: false,
        };
    },
    computed: {
        isVisible() {
            return !this.isCollapsible || this.toggle;
        },
        isCollapsible() {
            return this.obj.args.collapse !== undefined;
        },
    },
};
</script>
