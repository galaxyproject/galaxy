import { safeAssign } from "utils/safeAssign";
import { BaseModel } from "./BaseModel";

export class BcoConfig extends BaseModel {
    constructor(props = {}) {
        super();
        this.role_arn = "";
        safeAssign(this, props);
        this.updateState();
    }
}

BcoConfig.setValidator(function (model) {
    const errors = {};

    if (!model.server_address) {
        errors.tenant_id = "Missing Server Address";
    }

    if (!model.authorization) {
        errors.client_id = "Missing User API Key";
    }

    if (model.authorization == "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx") {
        errors.client_id = "Enter a valid API Key";
    }

    if (!model.client_secret) {
        errors.client_secret = "Missing secret";
    }

    return errors;
});

BcoConfig.fields = {
    server_address: {
        label: "Server Address",
        placeholder: "https://beta.portal.aws.biochemistry.gwu.edu",
        description: "The Client ID (or Application ID) you defined for Galaxy on your Azure directory.",
    },
    authorization: {
        label: "User API Key",
        mask: "********-****-****-****-************",
        placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        description: "Your Tenant ID (or Directory ID) on the BCODB server instance.",
    },
    owner_group: {
        label: "Group Permissions",
        placeholder: "bco_drafters",
        description:
            "A secret string you obtained from Azure portal that Galaxy can use to prove its identity when requesting tokens to access your resources.",
    },
    table: {
        label: "Database Table",
        placeholder: "bco_draft",
        description:
            "A secret string you obtained from Azure portal that Galaxy can use to prove its identity when requesting tokens to access your resources.",
    },
};
