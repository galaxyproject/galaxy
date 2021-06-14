import { AwsConfig } from "./AwsConfig";
import { AzureConfig } from "./AzureConfig";

export const ResourceProviders = new Map();

ResourceProviders.set("aws", {
    klass: AwsConfig,
    label: "Amazon Web Services (AWS)",
});

ResourceProviders.set("azure", {
    klass: AzureConfig,
    label: "Microsoft Azure",
});
