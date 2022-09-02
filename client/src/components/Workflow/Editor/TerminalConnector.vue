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
        },
    },
    computed: {
        position() {
            const outputPos = this.$store.getters["workflowState/getOutputTerminalPosition"](
                this.connection.outputStepId,
                this.connection.outputName
            );
            const inputPos = this.$store.getters["workflowState/getInputTerminalPosition"](
                this.connection.inputStepId,
                this.connection.inputName
            );
            if (inputPos && outputPos) {
                return {
                    ...inputPos,
                    ...outputPos,
                };
            }
        },
    },
};
</script>

<style></style>
