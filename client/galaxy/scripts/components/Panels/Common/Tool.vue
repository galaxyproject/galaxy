<template>
    <div :class="['toolTitle', rootClass]">
        <a v-if="tool.disabled" class="text-muted">
            <span v-if="!hideName">{{ tool.name }}</span>
            {{ tool.description }}
        </a>
        <a @click="onClick" :href="tool.link" :target="tool.target" v-else>
            <span class="labels">
                <span
                    v-for="(label, index) in tool.labels"
                    :class="['badge', 'badge-primary', `badge-${label}`]"
                    :key="index"
                >
                    {{ label }}
                </span>
            </span>
            <span v-if="!hideName" class="font-weight-bold">{{ tool.name }}</span>
            {{ tool.description }}
            <span
                v-b-tooltip.hover
                :class="['float-right', operationIcon]"
                :title="operationTitle"
                @click.stop.prevent="onOperation"
            />
        </a>
    </div>
</template>

<script>
import ariaAlert from "utils/ariaAlert";

export default {
    name: "Tool",
    props: {
        tool: {
            type: Object,
            required: true
        },
        operationTitle: {
            type: String
        },
        operationIcon: {
            type: String
        },
        noSection: {
            type: Boolean
        },
        hideName: {
            type: Boolean
        }
    },
    computed: {
        rootClass() {
            return this.noSection ? "" : "ml-2";
        }
    },
    methods: {
        onClick(e) {
            ariaAlert(`${this.tool.name} selected from panel`);
            this.$emit("onClick", e, this.tool);
        },
        onOperation(e) {
            ariaAlert(`${this.tool.name} operation selected from panel`);
            this.$emit("onOperation", e, this.tool);
        }
    }
};
</script>
