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
            <FormElement
                :id="getActionId('ChangeDatatypeAction', 'newtype')"
                :v-model="formData[getActionId('ChangeDatatypeAction', 'newtype')]"
                ignore="__empty__"
                title="Change datatype"
                type="text"
                help="This action will change the datatype of the output to the indicated datatype."
                @change="onChangeDatatype"
            />
            <FormElement
                :id="getActionId('TagDatasetAction', 'tags')"
                :v-model="formData[getActionId('TagDatasetAction', 'tags')]"
                ignore=""
                title="Add Tags"
                type="text"
                help="This action will set tags for the dataset."
                @change="onChange"
            />
            <FormElement
                :id="getActionId('RemoveTagDatasetAction', 'tags')"
                :v-model="formData[getActionId('RemoveTagDatasetAction', 'tags')]"
                ignore=""
                title="Remove Tags"
                type="text"
                help="This action will remove tags for the dataset."
                @change="onChange"
            />
            <FormCard title="Assign columns" collapsible :expanded.sync="expandedColumns">
                <template v-slot:body>
                    <FormElement
                        :id="getActionId('ColumnSetAction', 'chromCol')"
                        :v-model="formData[getActionId('ColumnSetAction', 'chromCol')]"
                        ignore=""
                        title="Chrom column"
                        type="text"
                        help="This action will set the chromosome column."
                        @change="onChange"
                    />
                    <FormElement
                        :id="getActionId('ColumnSetAction', 'startCol')"
                        :v-model="formData[getActionId('ColumnSetAction', 'startCol')]"
                        ignore=""
                        title="Start column"
                        type="text"
                        help="This action will set the start column."
                        @change="onChange"
                    />
                    <FormElement
                        :id="getActionId('ColumnSetAction', 'endCol')"
                        :v-model="formData[getActionId('ColumnSetAction', 'endCol')]"
                        ignore=""
                        title="End column"
                        type="text"
                        help="This action will set the end column."
                        @change="onChange"
                    />
                    <FormElement
                        :id="getActionId('ColumnSetAction', 'strandCol')"
                        :v-model="formData[getActionId('ColumnSetAction', 'strandCol')]"
                        ignore=""
                        title="Strand column"
                        type="text"
                        help="This action will set the strand column."
                        @change="onChange"
                    />
                    <FormElement
                        :id="getActionId('ColumnSetAction', 'nameCol')"
                        :v-model="formData[getActionId('ColumnSetAction', 'nameCol')]"
                        ignore=""
                        title="Name column"
                        type="text"
                        help="This action will set the name column."
                        @change="onChange"
                    />
                </template>
            </FormCard>
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
            expandedColumns: false,
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
        onChangeDatatype() {
            //onOutputDatatype;
        },
    },
};
</script>
