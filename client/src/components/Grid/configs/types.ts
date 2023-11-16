import { IconProp } from "@fortawesome/fontawesome-svg-core";
import type Router from "vue-router";

import Filtering from "@/utils/filtering";

export interface Action {
    title: string;
    icon?: IconProp;
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

export type FieldArray = Array<FieldKey | FieldOperations>;

interface FieldKey {
    key: string;
    title: string;
    disabled?: boolean;
    type: string;
    handler?: (data: RowData) => void;
}

export type FieldHandler = (data: RowData) => void;

export interface FieldOperations {
    key: string;
    title: string;
    type: string;
    condition?: (data: RowData) => boolean;
    operations: Array<Operation>;
    width?: number;
}

export interface Operation {
    title: string;
    icon: IconProp;
    condition?: (data: RowData) => boolean;
    handler: (data: RowData, router: Router) => OperationHandlerReturn;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = Promise<OperationHandlerMessage> | void;

export type RowData = Record<string, unknown>;
