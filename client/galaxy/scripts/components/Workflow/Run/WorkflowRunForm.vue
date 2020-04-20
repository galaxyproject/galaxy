<template>
    <div ref="form"></div>
</template>

<script>
import ToolFormComposite from "mvc/tool/tool-form-composite";

export default {
    props: {
        runData: {
            type: Object,
            required: true,
        },
        setRunButtonStatus: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            runForm: null,
        };
    },
    mounted() {
        this.$nextTick(() => {
            const el = this.$refs["form"];
            const formProps = {
                el,
                setRunButtonStatus: this.setRunButtonStatus,
                handleInvocations: this.handleInvocations,
            };
            this.runForm = new ToolFormComposite.View(Object.assign({}, this.runData, formProps));
        });
    },
    methods: {
        execute() {
            this.runForm.execute();
        },
        handleInvocations(invocations) {
            this.$emit("submissionSuccess", invocations);
        },
    },
};
</script>
