import { faAws, faPython } from "@fortawesome/free-brands-svg-icons";
import { faCloud, faHdd, faNetworkWired, type IconDefinition } from "font-awesome-6";

import type { components } from "@/api/schema";
import { contains } from "@/utils/filtering";

const typeMessage = (type: string) => `This template produces storage locations of type ${type}.`;

export type ObjectStoreTemplateSummary = components["schemas"]["ObjectStoreTemplateSummary"];
export type ObjectStoreTemplateSummaries = ObjectStoreTemplateSummary[];

export type ObjectStoreTypes = ObjectStoreTemplateSummary["type"];
export type ObjectStoreTypesDetail = Record<ObjectStoreTypes, { icon: IconDefinition; message: string }>;
export type ObjectStoreBadgeType = components["schemas"]["BadgeDict"];

export type ObjectStoreTemplateType = Record<ObjectStoreTypes, { icon: IconDefinition; message: string }>;
export const objectStoreTemplateTypes: ObjectStoreTemplateType = {
    aws_s3: {
        icon: faAws,
        message: typeMessage("Amazon S3"),
    },
    azure_blob: {
        icon: faCloud,
        message: typeMessage("Azure Blob"),
    },
    boto3: {
        icon: faPython,
        message: typeMessage("Boto3"),
    },
    disk: {
        icon: faHdd,
        message: typeMessage("Disk"),
    },
    generic_s3: {
        icon: faAws,
        message: typeMessage("Generic S3"),
    },
    onedata: {
        icon: faNetworkWired,
        message: typeMessage("Onedata"),
    },
};

export const ObjectStoreValidFilters = {
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
