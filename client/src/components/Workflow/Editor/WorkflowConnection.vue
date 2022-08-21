<template>
    <div v-if="canvasManager">{{ connections }}</div>
</template>
<script>
import Connector from "./modules/connector";

export default {
    // components: {
    //     WorkflowConnection
    // },
    props: {
        canvasManager: {
            type: Object,
            required: true,
        },
        step: {
            type: Object,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
    },
    computed: {
        connections() {
            Object.entries(this.step.input_connections).forEach(([k, v]) => {
                if (v) {
                    const source = `node-${this.step.id}-input-${k}`;
                    const inputTerminal = this.$store.getters.getInputTerminal(source);
                    if (!Array.isArray(v)) {
                        v = [v];
                    }
                    v.forEach((x) => {
                        const target = `node-${x.id}-output-${x.output_name}`;
                        let outputTerminal = this.$store.getters.getOutputTerminal(target);
                        console.log(outputTerminal);
                        if (inputTerminal && outputTerminal) {
                            const c = new Connector(this.canvasManager, outputTerminal, inputTerminal);
                            c.connect(outputTerminal, inputTerminal);
                            this.$store.commit("setConnection", source, target, c);
                            c.redraw();
                        }
                    });
                }
            });
        },
    },
};
</script>
