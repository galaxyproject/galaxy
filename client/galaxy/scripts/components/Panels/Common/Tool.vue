<template>
    <div :class="noSection ? 'toolTitleNoSection' : 'toolTitle'">
        <div>
            <a
                @click="open"
                :href="tool.link"
                :target="tool.target"
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
    methods: {
        open(e) {
            ariaAlert(`${this.tool.name} opened in center panel`);
            this.$emit("onOpen", e, this.tool);
        }
    }
};
</script>
