import { faAws, faDropbox, faGoogleDrive } from "@fortawesome/free-brands-svg-icons";
import { faCloud, faFolderTree, faNetworkWired, type IconDefinition } from "font-awesome-6";

import { type components } from "@/api/schema";
import { contains } from "@/utils/filtering";

export type FileSourceTemplateSummary = components["schemas"]["FileSourceTemplateSummary"];
export type FileSourceTemplateSummaries = FileSourceTemplateSummary[];

export type UserFileSourceModel = components["schemas"]["UserFileSourceModel"];
export type FileSourceTypes = UserFileSourceModel["type"];
export type FileSourceTypesDetail = Record<FileSourceTypes, { icon: IconDefinition; message: string }>;

export const templateTypes: FileSourceTypesDetail = {
    azure: {
        icon: faCloud,
        message: "基于 Azure 服务的远程文件源插件。",
    },
    dropbox: {
        icon: faDropbox,
        message: "与商业 Dropbox 服务连接的文件源插件。",
    },
    ftp: {
        icon: faNetworkWired,
        message: "基于 FTP 协议的远程文件源插件。",
    },
    googledrive: {
        icon: faGoogleDrive,
        message: "与商业 Google Drive 服务连接的文件源插件。",
    },
    onedata: {
        icon: faNetworkWired,
        message: "基于 Onedata 服务的远程文件源插件。",
    },
    posix: {
        icon: faFolderTree,
        message:
            "基于路径的简单文件源，假定所有相关路径已经在服务器和目标工作节点上挂载。",
    },
    s3fs: {
        icon: faAws,
        message:
            "基于 Amazon Simple Storage Service (S3) 接口的远程文件源插件。AWS 接口已成为行业标准，许多存储供应商支持并使用它来提供基于 '对象' 的存储。",
    },
    webdav: {
        icon: faNetworkWired,
        message: "基于 WebDAV 协议的远程文件源插件。",
    },
    elabftw: {
        icon: faNetworkWired,
        message: "与 eLabFTW 实例连接的远程文件源。",
    },
    inveniordm: {
        icon: faNetworkWired,
        message: "与 InvenioRDM 实例连接的远程文件源。",
    },
    zenodo: {
        icon: faNetworkWired,
        message: "与 Zenodo 实例连接的远程文件源。",
    },
};


export const FileSourcesValidFilters = {
    name: {
        placeholder: "name",
        type: String,
        handler: contains("name"),
        menuItem: false,
    },
    type: {
        placeholder: "type",
        type: String,
        handler: contains("type"),
        menuItem: false,
    },
};
