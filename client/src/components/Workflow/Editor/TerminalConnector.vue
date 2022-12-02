<template>
    <raw-connector v-if="position" :position="position"></raw-connector>
</template>

<script>
import RawConnector from "./Connector";

export default {
    components: {
        RawConnector,
    },
    props: {
        connection: {
            type: Object,
            required: true,
        },
    },
    computed: {
        position() {
            const outputPos = this.$store.getters["workflowState/getOutputTerminalPosition"](
                this.connection.output.stepId,
                this.connection.output.name
            );
            const inputPos = this.$store.getters["workflowState/getInputTerminalPosition"](
                this.connection.input.stepId,
                this.connection.input.name
            );
            if (inputPos && outputPos) {
                return {
                    ...inputPos,
                    ...outputPos,
                };
            }
            return null;
        },
    },
};
</script>

<style></style>
