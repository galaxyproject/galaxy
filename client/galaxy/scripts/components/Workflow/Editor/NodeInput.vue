<template>
    <div class="form-row dataRow input-data-row">
        {{ label }}
        <div v-if="showRemove" class="delete-terminal" @click="onRemove"/>
        <div ref="terminal" class="terminal input-terminal"/>
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
    },
    data() {
        return {
            showRemove: true
        }
    },
    computed: {
        label() {
            return this.input.label || this.input.name;
        },
    },
    methods: {
        onRemove() {
            /*const terminal = this.input.terminal;
            // If connected, create a popup to allow disconnection
            if (terminal.connectors.length > 0) {
                const t = $("<div/>")
                    .addClass("delete-terminal")
                    .click(() => {
                        $.each(terminal.connectors, (_, x) => {
                            if (x) {
                                x.destroy();
                            }
                        });
                        t.remove();
                    })
                    .on("mouseleave", () => {
                        t.remove();
                    });
                $(this.el).parent().append(t);
            }*/
        }
    }
};
</script>