import { computed, type Ref, ref } from "vue";

import type { AnyWorkflow } from "@/api/workflows";
import {
    copyWorkflow as copyWorkflowService,
    deleteWorkflow as deleteWorkflowService,
    updateWorkflow as updateWorkflowService,
} from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { copy } from "@/utils/clipboard";
import { withPrefix } from "@/utils/redirect";
import { getFullAppUrl } from "@/utils/utils";

export function useWorkflowActions(workflow: Ref<AnyWorkflow>, refreshCallback: () => void) {
    const toast = useToast();

    const bookmarkLoading = ref(false);

    const toggleBookmark = async (checked: boolean) => {
        try {
            bookmarkLoading.value = true;

            await updateWorkflowService(workflow.value.id, {
                show_in_tool_panel: checked,
            });

            toast.info(`工作流${checked ? "已添加到" : "已从"}收藏夹${checked ? "" : "中移除"}`);
        } catch (error) {
            toast.error("更新工作流收藏状态失败");
        } finally {
            refreshCallback();
            bookmarkLoading.value = false;
        }
    };

    const { confirm } = useConfirmDialog();

    const deleteWorkflow = async () => {
        const confirmed = await confirm("您确定要删除这个工作流吗？", {
            title: "删除工作流",
            okTitle: "删除",
            okVariant: "danger",
        });

        if (confirmed) {
            await deleteWorkflowService(workflow.value.id);
            refreshCallback();
            toast.info("工作流已删除");
        }
    };

    const relativeLink = computed(() => {
        return `/published/workflow?id=${workflow.value.id}`;
    });

    const fullLink = computed(() => {
        return getFullAppUrl(relativeLink.value.substring(1));
    });

    function copyPublicLink() {
        copy(fullLink.value);
        toast.success("工作流链接已复制");
    }

    async function copyWorkflow() {
        const confirmed = await confirm("您确定要复制这个工作流吗？", "复制工作流");

        if (confirmed) {
            await copyWorkflowService(workflow.value.id, workflow.value.owner);
            refreshCallback();
            toast.success("工作流已复制");
        }
    }

    const downloadUrl = computed(() => {
        return withPrefix(`/api/workflows/${workflow.value.id}/download?format=json-download`);
    });

    async function importWorkflow() {
        await copyWorkflowService(workflow.value.id, workflow.value.owner);
        toast.success("工作流导入成功");
    }

    return {
        bookmarkLoading,
        toggleBookmark,
        deleteWorkflow,
        copyPublicLink,
        copyWorkflow,
        importWorkflow,
        downloadUrl,
    };
}
