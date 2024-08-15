import { type FileSourceTemplateSummary } from "@/api/fileSources";
import { type UserConcreteObjectStore } from "@/components/ObjectStore/Instances/types";
import { type ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

export const STANDARD_OBJECT_STORE_TEMPLATE: ObjectStoreTemplateSummary = {
    type: "aws_s3",
    name: "moo",
    description: null,
    variables: [
        {
            name: "oldvar",
            type: "string",
            help: "old var help",
        },
        {
            name: "newvar",
            type: "string",
            help: "new var help",
        },
    ],
    secrets: [
        {
            name: "oldsecret",
            help: "old secret help",
        },
        {
            name: "newsecret",
            help: "new secret help",
        },
    ],
    id: "moo",
    version: 2,
    badges: [],
};

export const STANDARD_FILE_SOURCE_TEMPLATE: FileSourceTemplateSummary = {
    type: "s3fs",
    name: "moo",
    description: null,
    variables: [
        {
            name: "oldvar",
            type: "string",
            help: "old var help",
        },
        {
            name: "newvar",
            type: "string",
            help: "new var help",
        },
    ],
    secrets: [
        {
            name: "oldsecret",
            help: "old secret help",
        },
        {
            name: "newsecret",
            help: "new secret help",
        },
    ],
    id: "moo",
    version: 2,
};

export const GENERIC_FTP_FILE_SOURCE_TEMPLATE: FileSourceTemplateSummary = {
    id: "ftp",
    type: "ftp",
    name: "Generic FTP Server",
    description: "Generic FTP configuration with all configuration options exposed.",
    variables: [
        { name: "host", label: "FTP Host", type: "string", help: "Host of FTP Server to connect to." },
        {
            name: "user",
            label: "FTP User",
            type: "string",
            help: "Username to login to target FTP server with.",
        },
        {
            name: "writable",
            label: "Writable?",
            type: "boolean",
            help: "Is this an FTP server you have permission to write to?",
            default: false,
        },
        {
            name: "port",
            label: "FTP Port",
            type: "integer",
            help: "Port used to connect to the FTP server.",
            default: 21,
        },
    ],
    secrets: [
        {
            name: "password",
            label: "FTP Password",
            help: "Password to connect to FTP server with.",
        },
    ],
};

export const OBJECT_STORE_INSTANCE: UserConcreteObjectStore = {
    type: "aws_s3",
    name: "moo",
    description: undefined,
    template_id: "moo",
    template_version: 1,
    badges: [],
    variables: {
        oldvar: "my old value",
        droppedvar: "this will be dropped",
    },
    secrets: ["oldsecret", "droppedsecret"],
    quota: { enabled: false },
    private: false,
    uuid: "112f889f-72d7-4619-a8e8-510a8c685aa7",
    active: true,
    hidden: false,
    purged: false,
};
