<template>
    <div :class="rootClass">
        <a v-if="tool.disabled" class="text-muted">
            <span v-if="showName">{{ tool.name }}</span>
            {{ tool.description }}
        </a>
        <a @click="open" :href="tool.link" :target="tool.target" v-else>
            <span class="labels">
                <span
                    v-for="(label, index) in tool.labels"
                    :class="['badge', 'badge-primary', `badge-${label}`]"
                    :key="index"
                >
                    {{ label }}
                </span>
            </span>
            <span v-if="showName" class="font-weight-bold">{{ tool.name }}</span>
            {{ tool.description }}
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
        noSection: {
            type: Boolean,
            default: false
        },
        showName: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        rootClass() {
            return this.noSection ? "toolTitleNoSection" : "toolTitle";
        }
    },
    methods: {
        open(e) {
            ariaAlert(`${this.tool.name} opened in center panel`);
            this.$emit("onOpen", e, this.tool);
        }
    }
};
</script>
