<template>
    <div class="h-100">
        <ToolInteractiveClient
            v-if="isInteractiveClientTool"
            :tool-config="toolConfig"
            :show-tool="showTool"
            :disable-tool="disableTool"
            :loading="loading"
            @onChangeVersion="onChangeVersion"
            @onSetError="onSetError">
            <template v-slot:tool-messages>
                <slot name="tool-messages" />
            </template>
        </ToolInteractiveClient>
        <ToolForm
            v-else
            :tool-config="toolConfig"
            :show-tool="showTool"
            :disable-tool="disableTool"
            :loading="loading"
            @onChangeVersion="onChangeVersion"
            @onSetError="onSetError">
            <template v-slot:tool-messages>
                <slot name="tool-messages" />
            </template>
        </ToolForm>
    </div>
</template>

<script>
import ToolForm from "./ToolForm.vue";
import ToolInteractiveClient from "./ToolInteractiveClient.vue";

export default {
    components: {
        ToolForm,
        ToolInteractiveClient,
    },
    props: {
        toolConfig: {
            type: Object,
            required: true,
        },
        showTool: {
            type: Boolean,
            required: true,
        },
        disableTool: {
            type: Boolean,
            default: false,
        },
        loading: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        isInteractiveClientTool() {
            return this.toolConfig.model_class === "InteractiveClientTool";
        },
    },
    methods: {
        onChangeVersion(newVersion) {
            this.$emit("onChangeVersion", newVersion);
        },
        onSetError(errorObj) {
            this.$emit("onSetError", errorObj);
        },
    },
};
</script>
