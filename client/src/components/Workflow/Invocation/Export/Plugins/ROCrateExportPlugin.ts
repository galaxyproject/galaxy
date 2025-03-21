import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

export const RO_CRATE_EXPORT_PLUGIN: InvocationExportPlugin = {
    id: "ro-crate",
    title: "研究对象包装箱",
    img: "https://www.researchobject.org/workflow-run-crate/img/ro-crate-workflow-run.svg",
    url: "https://www.researchobject.org/workflow-run-crate/",
    markdownDescription: `
RO-Crate 是一个社区努力，旨在建立一种轻量级方法来将研究数据与其元数据打包在一起。它基于 schema.org 中的 JSON-LD 注解，旨在使形式元数据描述的最佳实践在更广泛的情况下变得易于访问和实用，从单个研究人员处理数据文件夹，到大型数据密集型计算研究环境。

在[这里](https://www.researchobject.org/workflow-run-crate/)了解更多信息。`,
    exportParams: {
        modelStoreFormat: "rocrate.zip",
        includeFiles: true,
        includeDeleted: false,
        includeHidden: false,
    },
};
