<template>
    <FormCard :title="outputTitle" collapsible :expanded.sync="expanded">
        <template v-slot:body>
            <FormElement
                :id="outputLabelId"
                :value="outputLabel"
                title="Label"
                type="text"
                help="This will provide a short name to describe the output - this must be unique across workflows."
                @input="onInputLabel"
            />
            <FormElement
                :id="actionNames.RenameDatasetAction__newname"
                :value="formData[actionNames.RenameDatasetAction__newname]"
                :help="renameHelp"
                ignore=""
                title="Rename dataset"
                type="text"
                @input="onInput"
            />
            <FormElement
                :id="actionNames.ChangeDatatypeAction__newtype"
                :value="formData[actionNames.ChangeDatatypeAction__newtype]"
                :options="extensions"
                ignore="__empty__"
                title="Change datatype"
                type="select"
                backbonejs
                help="This action will change the datatype of the output to the indicated datatype."
                @input="onInputDatatype"
            />
            <FormElement
                :id="actionNames.TagDatasetAction__tags"
                :value="formData[actionNames.TagDatasetAction__tags]"
                ignore=""
                title="Add Tags"
                type="text"
                help="This action will set tags for the dataset."
                @input="onInput"
            />
            <FormElement
                :id="actionNames.RemoveTagDatasetAction__tags"
                :value="formData[actionNames.RemoveTagDatasetAction__tags]"
                ignore=""
                title="Remove Tags"
                type="text"
                help="This action will remove tags for the dataset."
                @input="onInput"
            />
            <FormCard title="Assign columns" collapsible :expanded.sync="expandedColumns">
                <template v-slot:body>
                    <FormElement
                        :id="actionNames.ColumnSetAction__chromCol"
                        :value="formData[actionNames.ColumnSetAction__chromCol]"
                        ignore=""
                        title="Chrom column"
                        type="text"
                        help="This action will set the chromosome column."
                        @input="onInput"
                    />
                    <FormElement
                        :id="actionNames.ColumnSetAction__startCol"
                        :value="formData[actionNames.ColumnSetAction__startCol]"
                        ignore=""
                        title="Start column"
                        type="text"
                        help="This action will set the start column."
                        @input="onInput"
                    />
                    <FormElement
                        :id="actionNames.ColumnSetAction__endCol"
                        :value="formData[actionNames.ColumnSetAction__endCol]"
                        ignore=""
                        title="End column"
                        type="text"
                        help="This action will set the end column."
                        @input="onInput"
                    />
                    <FormElement
                        :id="actionNames.ColumnSetAction__strandCol"
                        :value="formData[actionNames.ColumnSetAction__strandCol]"
                        ignore=""
                        title="Strand column"
                        type="text"
                        help="This action will set the strand column."
                        @input="onInput"
                    />
                    <FormElement
                        :id="actionNames.ColumnSetAction__nameCol"
                        :value="formData[actionNames.ColumnSetAction__nameCol]"
                        ignore=""
                        title="Name column"
                        type="text"
                        help="This action will set the name column."
                        @input="onInput"
                    />
                </template>
            </FormCard>
        </template>
    </FormCard>
</template>

<script>
import FormCard from "components/Form/FormCard";
import FormElement from "components/Form/FormElement";

const actions = [
    "RenameDatasetAction__newname",
    "ChangeDatatypeAction__newtype",
    "TagDatasetAction__tags",
    "RemoveTagDatasetAction__tags",
    "ColumnSetAction__chromCol",
    "ColumnSetAction__startCol",
    "ColumnSetAction__endCol",
    "ColumnSetAction__strandCol",
    "ColumnSetAction__nameCol",
];

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
        formData: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            expanded: false,
            expandedColumns: false,
            renameHelpUrl: "https://galaxyproject.org/learn/advanced-workflow/variables/",
        };
    },
    computed: {
        node() {
            return this.getNode();
        },
        postJobActions() {
            return this.node.postJobActions;
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
        actionNames() {
            const index = {};
            actions.forEach((action) => {
                index[action] = `pja__${this.outputName}__${action}`;
            });
            return index;
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
            return list;
        },
        renameHelp() {
            const helpLink = `<a href="${this.renameHelpUrl}">here</a>`;
            const helpSection = `This action will rename the output dataset. Click ${helpLink} for more information. Valid input variables are:`;
            let helpLabels = "";
            for (const input of this.node.inputs) {
                const name = input.name.replace(/\|/g, ".");
                const label = input.label ? `(${input.label})` : "";
                helpLabels += `<li><strong>${name}</strong>${label}</li>`;
            }
            return `${helpSection}<ul>${helpLabels}</ul>`;
        },
    },
    methods: {
        onInput(id, value) {
            this.$emit("onInput", id, value);
        },
        onInputLabel(newLabel) {
            this.$emit("onInputLabel", this.outputName, newLabel);
        },
        onInputDatatype(newDatatype) {
            this.$emit("onInputDatatype", this.outputName, newDatatype);
        },
    },
};
</script>
