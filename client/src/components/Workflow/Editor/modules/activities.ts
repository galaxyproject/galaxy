import { faSave as farSave } from "@fortawesome/free-regular-svg-icons";
import {
    faDownload,
    faEdit,
    faHistory,
    faMagic,
    faPencilAlt,
    faPlay,
    faPlus,
    faRecycle,
    faSave,
    faSignOutAlt,
    faSitemap,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { watchImmediate } from "@vueuse/core";
import { faDiagramNext } from "font-awesome-6";
import { computed, type Ref } from "vue";

import { type Activity, useActivityStore } from "@/stores/activityStore";

export const workflowEditorActivities = [
    {
        title: "属性",
        id: "workflow-editor-attributes",
        tooltip: "编辑工作流属性",
        description: "查看和编辑此工作流的属性。",
        panel: true,
        icon: faPencilAlt,
        visible: true,
    },
    {
        title: "输入",
        id: "workflow-editor-inputs",
        tooltip: "向工作流添加输入步骤",
        description: "向工作流添加输入步骤。",
        icon: faDiagramNext,
        panel: true,
        visible: true,
    },
    {
        title: "工具",
        id: "workflow-editor-tools",
        description: "显示工具面板以搜索和放置所有可用工具。",
        icon: faWrench,
        panel: true,
        tooltip: "搜索在工作流中使用的工具",
        visible: true,
    },
    {
        title: "工作流",
        id: "workflow-editor-workflows",
        description: "浏览其他工作流并将它们添加为子工作流。",
        tooltip: "搜索在工作流中使用的工作流",
        icon: faSitemap,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "报告",
        id: "workflow-editor-report",
        description: "编辑此工作流的报告。",
        tooltip: "编辑工作流报告",
        icon: faEdit,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "最佳实践",
        id: "workflow-best-practices",
        description: "显示并测试此工作流中的最佳实践。",
        tooltip: "测试工作流是否符合最佳实践",
        icon: faMagic,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "变更",
        id: "workflow-undo-redo",
        description: "查看、撤销和重做您最近的更改。",
        tooltip: "显示和管理最近的更改",
        icon: faHistory,
        panel: true,
        visible: true,
        optional: true,
    },
    {
        title: "运行",
        id: "workflow-run",
        description: "使用特定参数运行此工作流。",
        tooltip: "运行工作流",
        icon: faPlay,
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "保存此工作流。",
        icon: faSave,
        id: "save-workflow",
        title: "保存",
        tooltip: "保存当前更改",
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "使用不同的名称和注释保存此工作流。",
        icon: farSave,
        id: "save-workflow-as",
        title: "另存为",
        tooltip: "保存此工作流的副本",
        visible: true,
        click: true,
        optional: true,
    },
    {
        title: "升级",
        id: "workflow-upgrade",
        description: "更新此工作流中使用的所有工具。",
        tooltip: "更新所有工具",
        icon: faRecycle,
        visible: true,
        click: true,
        optional: true,
    },
    {
        title: "下载",
        id: "workflow-download",
        description: "以'.ga'格式下载此工作流。",
        tooltip: "下载工作流",
        icon: faDownload,
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "保存此工作流并创建新工作流。",
        icon: faPlus,
        title: "创建新工作流",
        id: "workflow-create",
        tooltip: "保存此工作流并创建一个新的",
        visible: true,
        click: true,
        optional: true,
    },
    {
        description: "退出工作流编辑器并返回到开始屏幕。",
        icon: faSignOutAlt,
        id: "exit",
        title: "退出",
        tooltip: "退出工作流编辑器",
        visible: false,
        click: true,
        optional: true,
    },
] as const satisfies Readonly<Activity[]>;

interface ActivityLogicOptions {
    activityBarId: string;
    isNewTempWorkflow: boolean;
}

export function useActivityLogic(options: Ref<ActivityLogicOptions>) {
    const store = useActivityStore(options.value.activityBarId);

    watchImmediate(
        () => options.value.isNewTempWorkflow,
        (value) => {
            store.setMeta("workflow-run", "disabled", value);
        }
    );
}

interface SpecialActivityOptions {
    hasInvalidConnections: boolean;
}

export function useSpecialWorkflowActivities(options: Ref<SpecialActivityOptions>) {
    const saveHover = computed(() => {
        if (options.value.hasInvalidConnections) {
            return "工作流存在无效连接，请检查并移除无效连接";
        } else {
            return "保存此工作流，然后退出工作流编辑器";
        }
    });

    const specialWorkflowActivities = computed<Activity[]>(() => [
        {
            description: "",
            icon: faSave,
            id: "save-and-exit",
            title: "保存并退出",
            tooltip: saveHover.value,
            visible: false,
            click: true,
            mutable: false,
        },
    ]);

    return {
        specialWorkflowActivities,
    };
}
