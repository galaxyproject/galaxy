<template>
    <GModal
        v-model="show"
        :title="title"
        scrollable
        :hide-header-close="true"
        :no-close-on-esc="!error"
        :no-close-on-backdrop="!error"
        :hide-footer="!error"
        ok-only
        @ok="onOk"
        @hidden="onHidden">
        <div class="workflow-message-modal">
            <div v-if="message == 'progress'">
                <div class="progress progress-striped active">
                    <div class="progress-bar" style="width: 100%"></div>
                </div>
            </div>
            <div v-else>
                {{ message }}
            </div>
        </div>
    </GModal>
</template>

<script>
import { GModal } from "@/component-library";

export default {
    components: {
        GModal,
    },
    props: {
        title: {
            type: String,
            required: false,
            default: undefined,
        },
        message: {
            type: String,
            required: false,
            default: undefined,
        },
        error: {
            type: Boolean,
            required: false,
            default: undefined,
        },
    },
    data() {
        return {
            show: !!this.title,
        };
    },
    computed: {},
    watch: {
        message() {
            this.show = !!this.title;
        },
    },
    methods: {
        onHidden() {
            this.$emit("onHidden");
        },
        onOk() {
            // no-op I suppose...
        },
    },
};
</script>
