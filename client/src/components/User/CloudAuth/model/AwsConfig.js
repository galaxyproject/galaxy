import { safeAssign } from "utils/safeAssign";
import { BaseModel } from "./BaseModel";

export class AwsConfig extends BaseModel {
    constructor(props = {}) {
        super();
        this.role_arn = "";
        safeAssign(this, props);
        this.updateState();
    }
}

AwsConfig.setValidator(function (model) {
    const errors = {};
    if (!model.role_arn.length) {
        errors.role_arn = "Missing role_arn";
    }
    return errors;
});

AwsConfig.fields = {
    role_arn: {
        label: "Role ARN",
        description: "The Amazon resource name (ARN) of the role to be assumed by Galaxy.",
        placeholder: "arn:aws:iam::XXXXXXXXXXXX:role/XXXXXXXXXXX",
    },
};
