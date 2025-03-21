<template>
    <FormCard :title="outputTitle" collapsible :expanded.sync="expanded">
        <template v-slot:body>
            <FormOutputLabel :name="outputName" :step="step" />
            <FormElement
                :id="actionNames.RenameDatasetAction__newname"
                :value="formData[actionNames.RenameDatasetAction__newname]"
                :help="renameHelp"
                title="重命名数据集"
                type="text"
                @input="onInput" />
            <FormDatatype
                :id="actionNames.ChangeDatatypeAction__newtype"
                :value="formData[actionNames.ChangeDatatypeAction__newtype]"
                :datatypes="datatypes"
                title="更改数据类型"
                help="此操作将把输出的数据类型更改为指定的数据类型。"
                @onChange="onDatatype" />
            <FormElement
                :id="actionNames.TagDatasetAction__tags"
                :value="formData[actionNames.TagDatasetAction__tags]"
                :attributes="{ placeholder: '输入标签' }"
                title="添加标签"
                type="tags"
                help="此操作将为数据集设置标签。"
                @input="onInput" />
            <FormElement
                :id="actionNames.RemoveTagDatasetAction__tags"
                :value="formData[actionNames.RemoveTagDatasetAction__tags]"
                :attributes="{ placeholder: '输入标签' }"
                title="删除标签"
                type="tags"
                help="此操作将删除数据集的标签。"
                @input="onInput" />
            <FormCard title="分配列" collapsible :expanded.sync="expandedColumn">
                <template v-slot:body>
                    <FormElement
                        :id="actionNames.ColumnSetAction__chromCol"
                        :value="formData[actionNames.ColumnSetAction__chromCol]"
                        title="染色体列"
                        type="integer"
                        help="此操作将设置染色体列。"
                        @input="onInput" />
                    <FormElement
                        :id="actionNames.ColumnSetAction__startCol"
                        :value="formData[actionNames.ColumnSetAction__startCol]"
                        title="起始列"
                        type="integer"
                        help="此操作将设置起始列。"
                        @input="onInput" />
                    <FormElement
                        :id="actionNames.ColumnSetAction__endCol"
                        :value="formData[actionNames.ColumnSetAction__endCol]"
                        title="结束列"
                        type="integer"
                        help="此操作将设置结束列。"
                        @input="onInput" />
                    <FormElement
                        :id="actionNames.ColumnSetAction__strandCol"
                        :value="formData[actionNames.ColumnSetAction__strandCol]"
                        title="链列"
                        type="integer"
                        help="此操作将设置链列。"
                        @input="onInput" />
                    <FormElement
                        :id="actionNames.ColumnSetAction__nameCol"
                        :value="formData[actionNames.ColumnSetAction__nameCol]"
                        title="名称列"
                        type="integer"
                        help="此操作将设置名称列。"
                        @input="onInput" />
                </template>
            </FormCard>
        </template>
    </FormCard>
</template>

<script>
import FormCard from "@/components/Form/FormCard";
import FormElement from "@/components/Form/FormElement";
import FormDatatype from "@/components/Workflow/Editor/Forms/FormDatatype";
import FormOutputLabel from "@/components/Workflow/Editor/Forms/FormOutputLabel";

const actions = [
    "RenameDatasetAction__newname",
    "ChangeDatatypeAction__newtype",
    "TagDatasetAction__tags",
    "RemoveTagDatasetAction__tags",
];

const actionsColumn = [
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
        FormOutputLabel,
        FormDatatype,
    },
    props: {
        outputName: {
            type: String,
            required: true,
        },
        outputLabel: {
            type: String,
            default: null,
        },
        inputs: {
            type: Array,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
        formData: {
            type: Object,
            required: true,
        },
        step: {
            // type Step from @/stores/workflowStepStore
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            expanded: false,
            expandedColumn: false,
            renameHelpUrl: "https://galaxyproject.org/learn/advanced-workflow/variables/",
        };
    },
    computed: {
        outputTitle() {
            const title = this.outputLabel || this.outputName;
            return `Configure Output: '${title}'`;
        },
        actionNames() {
            const index = {};
            actions.concat(actionsColumn).forEach((action) => {
                index[action] = `pja__${this.outputName}__${action}`;
            });
            return index;
        },
        renameHelp() {
            /* TODO: FormElement should provide a slot for custom help templating instead. */
            const helpLink = `<a href="${this.renameHelpUrl}">此处</a>`;
            const helpSection = `此操作将重命名输出数据集。点击${helpLink}获取更多信息。有效的输入变量包括：`;
            let helpLabels = "";
            for (const input of this.inputs) {
                const name = input.name.replace(/\|/g, ".");
                const label = input.label ? `(${input.label})` : "";
                helpLabels += `<li><strong>${name}</strong>${label}</li>`;
            }
            return `${helpSection}<ul>${helpLabels}</ul>`;
        },
    },
    created() {
        this.setExpanded();
    },
    methods: {
        setExpanded() {
            this.expandedColumn = this.hasActions(actionsColumn);
            if (this.expandedColumn) {
                this.expanded = true;
            } else {
                this.expanded = this.hasActions(actions);
            }
        },
        hasActions(actions) {
            for (const key of actions) {
                if (this.formData[this.actionNames[key]] != undefined) {
                    return true;
                }
            }
            return false;
        },
        onInput(value, pjaKey) {
            this.$emit("onInput", value, pjaKey);
        },
        onDatatype(newDatatype) {
            this.$emit("onDatatype", this.actionNames.ChangeDatatypeAction__newtype, this.outputName, newDatatype);
        },
    },
};
</script>
