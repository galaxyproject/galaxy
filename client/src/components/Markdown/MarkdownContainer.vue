<template>
    <div>
        <b-button v-if="isCollapsible" class="m-1" @click="toggle != toggle">
            Toggle Collapse
        </b-button>
        <b-collapsible v-model="toggle">
            <markdown-element
                :obj="obj"
                :datasets="datasets"
                :collections="collections"
                :histories="histories"
                :invocations="invocations"
                :jobs="jobs"
                :workflows="workflows"
            />
        </b-collapsible>
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
        }
    },
    computed: {
        isCollapsible() {
            return this.obj.args.collapsed !== undefined;
        },
    },
};
</script>
