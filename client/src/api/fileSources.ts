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
        message: "This is a repository plugin based on the Azure service.",
    },
    dropbox: {
        icon: faDropbox,
        message: "This is a repository plugin that connects with the commercial Dropbox service.",
    },
    ftp: {
        icon: faNetworkWired,
        message: "This is a repository plugin based on the FTP/S protocol.",
    },
    googledrive: {
        icon: faGoogleDrive,
        message: "This is a  repository plugin that connects with the commercial Google Drive service.",
    },
    onedata: {
        icon: faNetworkWired,
        message: "This is a repository plugin based on the Onedata service.",
    },
    posix: {
        icon: faFolderTree,
        message:
            "This is a simple path based file source that assumes the all the relevant paths are already mounted on the Galaxy server and target worker nodes.",
    },
    s3fs: {
        icon: faAws,
        message:
            "This is a repository plugin based on the Amazon Simple Storage Service (S3) interface. The AWS interface has become an industry standard and many storage vendors support it and use it to expose 'object' based storage.",
    },
    webdav: {
        icon: faNetworkWired,
        message: "This is a repository plugin based on the WebDAV protocol.",
    },
    elabftw: {
        icon: faNetworkWired,
        message: "This is a repository plugin that connects with an eLabFTW instance.",
    },
    inveniordm: {
        icon: faNetworkWired,
        message: "This is a repository plugin that connects with an InvenioRDM instance.",
    },
    zenodo: {
        icon: faNetworkWired,
        message: "This is a repository plugin that connects with the Zenodo instance.",
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
