<template>
    <div :class="rootClass">
        <a
            @click="open"
            :href="tool.link"
            :target="tool.target"
            :class="anchorClass"
        >
            <span class="labels">
                <span
                    v-for="(label, index) in tool.labels"
                    :class="['badge', 'badge-primary', `badge-${label}`]"
                    :key="index"
                >
                    {{ label }}
                </span>
            </span>
            <span class="font-weight-bold">{{ tool.name }}</span>
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
        }
    },
    computed: {
        anchorClass() {
            return !this.tool.disabled && "text-muted";
        },
        rootClass() {
            return this.noSection ? 'toolTitleNoSection' : 'toolTitle';
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
