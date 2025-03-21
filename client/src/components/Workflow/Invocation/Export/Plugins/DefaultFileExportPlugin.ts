import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

export const DEFAULT_FILE_EXPORT_PLUGIN: InvocationExportPlugin = {
    id: "default-file",
    title: "压缩文件",
    markdownDescription: `将调用导出为包含 Galaxy 原生格式调用数据的压缩文件。`,
    exportParams: {
        modelStoreFormat: "tgz",
        includeFiles: false,
        includeDeleted: false,
        includeHidden: false,
    },
};
