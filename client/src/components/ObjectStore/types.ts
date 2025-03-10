import { type DatasetStorageDetails } from "@/api";
import { type components } from "@/api/schema";

export type ConcreteObjectStoreModel = components["schemas"]["ConcreteObjectStoreModel"];

export type AnyStorageDescription = DatasetStorageDetails | ConcreteObjectStoreModel;
