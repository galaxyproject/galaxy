import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

export const BIO_COMPUTE_OBJ_EXPORT_PLUGIN: InvocationExportPlugin = {
    id: "bco",
    title: "BioCompute 对象",
    img: "https://www.biocomputeobject.org/static/media/logo.c8a91f1656efbad5d745.png",
    url: "https://biocomputeobject.org/",
    markdownDescription: `
BioCompute 对象 (BCO) 是遵循 [IEEE-2791-2020 标准](https://standards.ieee.org/ieee/2791/7337/) 的 JSON 对象的非官方名称。
BCO 旨在传达高通量测序 (HTS) 分析结果、数据集创建、数据管理和生物信息学验证协议。

了解更多关于 [BioCompute 对象](https://biocomputeobject.org/) 的信息。

[使用 Galaxy 创建 BCO](https://w3id.org/biocompute/tutorials/galaxy_quick_start) 的说明。`,
    exportParams: {
        modelStoreFormat: "bco.json",
        includeFiles: false,
        includeDeleted: false,
        includeHidden: false,
    },
};
