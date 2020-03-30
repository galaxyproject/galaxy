<template>
    <div class="form-row dataRow input-data-row">
        {{ label }}
        <div ref="terminal" class="terminal input-terminal" @mouseover="mouseOver" @mouseleave="mouseLeave">
            <div v-if="showRemove" class="delete-terminal" @click="onRemove" />
        </div>
    </div>
</template>

<script>
export default {
    props: {
        input: {
            type: Object,
            required: true,
        },
        manager: {
            type: Object,
            required: true,
        },
        getTerminal: {
            type: Function,
            required: true
        }
    },
    data() {
        return {
            showRemove: false
        }
    },
    computed: {
        label() {
            return this.input.label || this.input.name;
        },
    },
    methods: {
        onRemove() {
            this.$emit("onRemove");
            const terminal = this.getTerminal();
            if (terminal.connectors.length > 0) {
                terminal.connectors.forEach((x) => {
                    if (x) {
                        x.destroy();
                    }
                });
            }
        },
        mouseOver() {
            this.showRemove = true;
        },
        mouseLeave() {
            this.showRemove = false;
        }
    }
};
</script>