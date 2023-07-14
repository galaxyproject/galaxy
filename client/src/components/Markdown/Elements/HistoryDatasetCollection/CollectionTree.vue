<template>
    <div>
        <span v-if="!skipHead" class="label">
            <b>{{ name }}</b>
        </span>
        <GAlert v-if="!!error" variant="danger" show> Error: {{ error }} </GAlert>
        <pre v-if="miscInfo">
          <code v-html="miscInfo"/>
        </pre>
        <pre v-if="peek">
          <code v-html="peek"/>
        </pre>
        <div v-if="node && node.elements && node.elements.length" :class="{ 'ml-3': !skipHead }">
            <CollectionNode v-for="child in node.elements" :key="child.id" :node="child" />
        </div>
    </div>
</template>

<script>
import GAlert from "@/component-library/GAlert.vue";

export default {
    name: "CollectionNode",
    components: {
        GAlert,
    },
    props: {
        node: {
            type: Object,
            default: null,
        },
        skipHead: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        name() {
            return this.node && (this.node.name || this.node.element_identifier || "n/a");
        },
        miscInfo() {
            return this.node && this.node.object && this.node.object.misc_info;
        },
        peek() {
            return this.node && this.node.object && this.node.object.peek;
        },
        url() {
            return this.node && this.node.object && this.node.object.url;
        },
        error() {
            return this.node && this.node.object && this.node.object.status === "error";
        },
    },
};
</script>
