<template>
    <div :class="['toolTitle', rootClass]">
        <a v-if="tool.disabled" class="text-muted">
            <span v-if="showName">{{ tool.name }}</span>
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
            return this.noSection ? "" : "ml-2";
        }
    },
    methods: {
        onClick(e) {
            ariaAlert(`${this.tool.name} selected from panel`);
            this.$emit("onClick", e, this.tool);
        }
    }
};
</script>
