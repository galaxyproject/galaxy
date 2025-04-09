<template>
    <div class="toolTitle">
        <a v-if="tool.disabled" :data-tool-id="tool.id" class="title-link name text-muted">
            <span v-if="!hideName">{{ tool.name }}</span>
            <span class="description">{{ tool.description }}</span>
        </a>
        <a
            v-else
            :class="targetClass"
            :data-tool-id="tool.id"
            :href="tool.link"
            :target="tool.target"
            :title="tool.help"
            @click="onClick">
            <img v-if="renderIcon && toolIconHref" class="icon" :src="toolIconHref" :alt="`${tool.name} logo`" />
            <!-- See if/where logo is actually used and unify?  Was this just apocyrphal visualizatinos maybe? -->
            <img v-if="tool.logo" class="logo" :src="tool.logo" :alt="tool.name" />
            <span class="labels">
                <span
                    v-for="(label, index) in tool.labels"
                    :key="index"
                    :class="['badge', 'badge-primary', `badge-${label}`]">
                    {{ label }}
                </span>
            </span>
            <span v-if="!hideName" class="name font-weight-bold">{{ tool.name }}</span>
            <span class="description">{{ tool.description }}</span>
            <span
                v-b-tooltip.hover
                :class="['operation', 'float-right', operationIcon]"
                :title="operationTitle"
                @click.stop.prevent="onOperation" />
        </a>
    </div>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import ariaAlert from "utils/ariaAlert";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    name: "Tool",
    props: {
        tool: {
            type: Object,
            required: true,
        },
        operationTitle: {
            type: String,
            default: "",
        },
        operationIcon: {
            type: String,
            default: "",
        },
        hideName: {
            type: Boolean,
            default: false,
        },
        toolKey: {
            type: String,
            default: "",
        },
        renderIcon: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        targetClass() {
            if (this.toolKey) {
                return `tool-menu-item-${this.tool[this.toolKey]} title-link cursor-pointer`;
            } else {
                return `title-link cursor-pointer`;
            }
        },
        toolIconHref() {
            return this.tool.icon ? `${getAppRoot()}api/tools/${this.tool.id}/icon/` : null;
        },
    },
    methods: {
        onClick(evt) {
            ariaAlert(`${this.tool.name} selected from panel`);
            this.$emit("onClick", this.tool, evt);
        },
        onOperation(evt) {
            ariaAlert(`${this.tool.name} operation selected from panel`);
            this.$emit("onOperation", this.tool, evt);
        },
    },
};
</script>

<style scoped>
.toolTitle {
    overflow-wrap: anywhere;
}
.logo {
    width: 2.5rem;
}
.icon {
    width: 2.5rem;
    margin-right: 0.5rem;
}
</style>
