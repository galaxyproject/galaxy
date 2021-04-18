<template>
    <Form :id="id" :inputs="inputs" ref="form" @onChange="onChange" />
</template>

<script>
import Form from "components/Form/Form";
import makeSection from "./makeSection";

export default {
    components: {
        Form,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
    },
    computed: {
        inputs() {
            const node = this.getNode();
            const datatypes = this.datatypes;
            return makeSection(
                node,
                datatypes,
                (node, outputName, newLabel) => {
                    const formVue = this.$refs["form"];
                    if (formVue && formVue.form) {
                        const form = formVue.form;
                        form.data.create();
                        const oldLabel = node.labelOutput(outputName, newLabel);
                        const input_id = form.data.match(`__label__${outputName}`);
                        const input_element = form.element_list[input_id];
                        if (oldLabel) {
                            input_element.field.model.set("value", oldLabel);
                            input_element.model.set(
                                "error_text",
                                `Duplicate output label '${newLabel}' will be ignored.`
                            );
                        } else {
                            input_element.model.set("error_text", "");
                        }
                        form.trigger("change");
                    }
                },
                (node, outputName, newDatatype) => {
                    node.changeOutputDatatype(outputName, newDatatype);
                }
            );
        },
    },
    methods: {
        onChange(values) {
            this.$emit("onChange", values);
        },
    },
};
</script>
