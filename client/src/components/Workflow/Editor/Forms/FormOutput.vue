<template>
    <FormCard :title="outputTitle" collapsible :expanded.sync="expanded">
        <template v-slot:body>
            <FormElement
                :id="outputLabelId"
                :value="outputLabel"
                title="Label"
                type="text"
                help="This will provide a short name to describe the output - this must be unique across workflows."
                @change="onChangeLabel"
            />
            <FormElement
                :id="getActionId('RenameDatasetAction', 'newname')"
                :v-model="formData[getActionId('RenameDatasetAction', 'newname')]"
                ignore=""
                title="Rename dataset"
                type="text"
                help="renameHelp"
                @change="onChange"
            />
        </template>
    </FormCard>
</template>

<script>
import FormCard from "components/Form/FormCard";
import FormElement from "components/Form/FormElement";

export default {
    components: {
        FormCard,
        FormElement,
    },
    props: {
        output: {
            type: Object,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        datatypes: {
            type: Array,
            default: null,
        },
    },
    data() {
        return {
            expanded: false,
            formData: {},
        }
    },
    computed: {
        node() {
            return this.getNode();
        },
        postJobActions() {
            return this.node.postJobActions;
        },
        extensions() {
            const list = [];
            for (const key in this.datatypes) {
                list.push({ 0: this.datatypes[key], 1: this.datatypes[key] });
            }
            list.sort((a, b) => (a.label > b.label ? 1 : a.label < b.label ? -1 : 0));
            list.unshift({
                0: "Sequences",
                1: "Sequences",
            });
            list.unshift({
                0: "Roadmaps",
                1: "Roadmaps",
            });
            list.unshift({
                0: "Leave unchanged",
                1: "__empty__",
            });
        },
        labels() {
            const list = [];
            for (const input of this.node.inputs) {
                list.push({ name: input.name, label: input.label });
            }
            return list;
        },
        activeOutput() {
            return this.node.activeOutputs.get(this.output.name);
        },
        outputTitle() {
            const title = this.output.label || this.output.name;
            return `Configure Output: '${title}'`;
        },
        outputName() {
            return this.output.name;
        },
        outputLabel() {
            return this.activeOutput && this.activeOutput.label;
        },
        outputLabelId() {
            return `__label__${this.output.name}`;
        },
    },
    methods: {
        getActionId(action, arg = null) {
            let id = `pja__${this.outputName}__${action}`;
            if (arg) {
                id += `__${arg}`;
            }
            return id;
        },
        onChange(values) {
            this.$emit("onChange", values);
        },
        onChangeLabel(newLabel) {
            //onOutputLabel(node, output.name, newLabel);
        },
    },
};
</script>
