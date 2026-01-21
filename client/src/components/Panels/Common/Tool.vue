<template>
    <div class="toolTitle">
        <a v-if="tool.disabled" :data-tool-id="tool.id" class="title-link name text-muted tool-link">
            <span v-if="!hideName">{{ tool.name }}</span>
            <span class="description">{{ tool.description }}</span>
        </a>
        <a
            v-else
            :class="targetClass"
            :data-tool-id="tool.id"
            :href="toolLink"
            :target="toolTarget"
            :title="tool.help"
            @click="onClick">
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
        <ToolFavoriteButton
            v-if="showFavoriteAction"
            :id="tool.id"
            :class="['tool-favorite-button', { 'tool-favorite-button-hover': showFavoriteOnHover }]"
            :data-tool-id="tool.id"
            color="grey" />
    </div>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import { storeToRefs } from "pinia";
import Vue, { computed } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import ariaAlert from "@/utils/ariaAlert";

import ToolFavoriteButton from "@/components/Tool/Buttons/ToolFavoriteButton.vue";

Vue.use(BootstrapVue);

export default {
    name: "Tool",
    components: {
        ToolFavoriteButton,
    },
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
        showFavoriteButton: {
            type: Boolean,
            default: false,
        },
    },
    setup(props) {
        const toolStore = useToolStore();
        const userStore = useUserStore();
        const { currentFavorites } = storeToRefs(userStore);
        const isFavorite = computed(() => currentFavorites.value.tools?.includes(props.tool.id));
        return {
            getLinkById: toolStore.getLinkById,
            getTargetById: toolStore.getTargetById,
            isFavorite,
        };
    },
    computed: {
        toolLink() {
            return this.getLinkById(this.tool.id);
        },
        toolTarget() {
            return this.getTargetById(this.tool.id);
        },
        targetClass() {
            if (this.toolKey) {
                return `tool-menu-item-${this.tool[this.toolKey]} title-link cursor-pointer tool-link`;
            } else {
                return `title-link cursor-pointer tool-link`;
            }
        },
        showFavoriteAction() {
            return this.showFavoriteButton || this.isFavorite;
        },
        showFavoriteOnHover() {
            return this.isFavorite;
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
    display: flex;
    align-items: flex-start;
    overflow-wrap: anywhere;
}
.tool-link {
    flex: 1 1 auto;
}
.tool-favorite-button {
    margin-left: 0.25rem;
}
.tool-favorite-button-hover {
    opacity: 0;
    transition: opacity 0.2s ease;
    transition-delay: 0s;
    pointer-events: none;
}
.toolTitle:hover .tool-favorite-button-hover {
    opacity: 1;
    transition-delay: 0.5s;
    pointer-events: auto;
}
.toolTitle:focus-within .tool-favorite-button-hover {
    opacity: 1;
    transition-delay: 0s;
    pointer-events: auto;
}
.tool-favorite-button-hover:focus {
    opacity: 1;
    transition-delay: 0s;
    pointer-events: auto;
}
</style>
