import { safeAssign } from "utils/safeAssign";
import { BaseModel } from "./BaseModel";

export class AzureConfig extends BaseModel {
    constructor(props = {}) {
        super();
        this.tenant_id = "";
        this.client_id = "";
        this.client_secret = "";
        safeAssign(this, props);
        this.updateState();
    }
}

AzureConfig.setValidator(function (model) {
    const errors = {};

    if (model.tenant_id.length < 36) {
        errors.tenant_id = "Tenant ID too short";
    }
    if (!model.tenant_id) {
        errors.tenant_id = "Missing Tenant ID";
    }

    if (model.client_id.length < 36) {
        errors.client_id = "Client ID too short";
    }
    if (!model.client_id) {
        errors.client_id = "Missing client ID";
    }

    if (!model.client_secret) {
        errors.client_secret = "Missing secret";
    }

    return errors;
});

AzureConfig.fields = {
    tenant_id: {
        label: "Tenant ID",
        mask: "********-****-****-****-************",
        placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        maxlength: 36,
        description: "Your Tenant ID (or Directory ID) on Azure.",
    },
    client_id: {
        label: "Client ID",
        mask: "********-****-****-****-************",
        placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        maxlength: 36,
        description: "The Client ID (or Application ID) you defined for Galaxy on your Azure directory.",
    },
    client_secret: {
        label: "Client Secret",
        mask: "",
        placeholder: "Client Secret",
        description:
            "A secret string you obtained from Azure portal that Galaxy can use to prove its identity when requesting tokens to access your resources.",
    },
};
