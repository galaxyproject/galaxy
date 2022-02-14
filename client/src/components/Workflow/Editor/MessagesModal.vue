<template>
    <b-modal
        v-model="show"
        :title="title"
        scrollable
        @ok="onOk"
        :hide-header-close="true"
        :no-close-on-esc="!error"
        :no-close-on-backdrop="!error"
        :hide-footer="!error"
        ok-only
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
    </b-modal>
</template>

<script>
export default {
    props: {
        title: {
            type: String,
            required: false,
        },
        message: {
            type: String,
            required: false,
        },
        error: {
            type: Boolean,
            required: false,
        },
    },
    data() {
        return {
            show: !!this.title,
        };
    },
    computed: {},
    methods: {
        onHidden() {
            this.$emit("onHidden");
        },
        onOk() {
            // no-op I suppose...
        },
    },
    watch: {
        message() {
            this.show = !!this.title;
        },
    },
};
</script>
