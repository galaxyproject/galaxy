import { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import type Router from "vue-router";

import Filtering from "@/utils/filtering";

export interface Action {
    title: string;
    icon?: IconDefinition;
    handler: (router: Router) => void;
}

export type ActionArray = Array<Action>;

export interface Config {
    actions?: ActionArray;
    fields: FieldArray;
    filtering: Filtering<any>;
    getData: (offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) => Promise<any>;
    plural: string;
    sortBy: string;
    sortKeys: Array<string>;
    sortDesc: boolean;
    title: string;
}

export type FieldArray = Array<FieldEntry>;

export interface FieldEntry {
    key: string;
    title: string;
    condition?: (data: RowData) => boolean;
    disabled?: boolean;
    type: string;
    operations?: Array<Operation>;
    handler?: FieldHandler;
    width?: number;
}

export type FieldHandler = (data: RowData, router?: Router) => void;

export interface Operation {
    title: string;
    icon: IconDefinition;
    condition?: (data: RowData) => boolean;
    handler: (data: RowData, router: Router) => OperationHandlerReturn;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = Promise<OperationHandlerMessage> | void;

export type RowData = Record<string, unknown>;
