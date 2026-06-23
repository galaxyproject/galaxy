import type { ColDef, ValueSetterParams } from "ag-grid-community";

import { Toast } from "@/composables/toast";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";

export function enforceColumnUniqueness(colDef: ColDef) {
    colDef.valueSetter = (params: ValueSetterParams) => {
        const newValue = params.newValue;
        const rowIndex = params.node?.rowIndex ?? -1;
        let isDuplicate = false;
        params.api.forEachNode((node) => {
            if (node.rowIndex !== rowIndex && node.data[params.colDef.field!] === newValue) {
                Toast.error("Element identifier values must be unique, supplied value already exists.");
                isDuplicate = true;
            }
        });
        if (isDuplicate) {
            return false; // Prevent duplicate values
        } else {
            params.data[params.colDef.field!] = newValue;
            return true;
        }
    };
}

export function useGridHelpers() {
    const { effectiveExtensions, listDbKeys } = useUploadConfigurations(undefined);

    function makeExtensionColumn(colDef: ColDef) {
        const options = () => {
            return effectiveExtensions.value.map((ext) => {
                return ext.id;
            });
        };
        // The select is too big for the free version of the select cell editor,
        // we need to replicate some of the functionality of the enterprise version.
        // colDef.cellEditor = "agSelectCellEditor";
        colDef.cellEditorParams = () => {
            return {
                values: options(),
            };
        };
        colDef.valueSetter = (params: ValueSetterParams) => {
            // If the value is not in the list of options, we don't want to set it.
            if (options().indexOf(params.newValue) === -1) {
                Toast.error(`Unknown file extension: ${params.newValue}.`);
                return false;
            }
            params.data[params.colDef.field!] = params.newValue;
            return true;
        };
    }

    function makeDbkeyColumn(colDef: ColDef) {
        const options = () => {
            return listDbKeys.value.map((dbKey) => {
                return dbKey.id;
            });
        };
        // The select is too big for the free version of the select cell editor,
        // we need to replicate some of the functionality of the enterprise version.
        // colDef.cellEditor = "agSelectCellEditor";
        colDef.cellEditorParams = () => {
            return {
                values: options(),
            };
        };
        colDef.valueSetter = (params: ValueSetterParams) => {
            // If the value is not in the list of options, we don't want to set it.
            if (options().indexOf(params.newValue) === -1) {
                Toast.error(`Unknown dbkey: ${params.newValue}.`);
                return false;
            }
            params.data[params.colDef.field!] = params.newValue;
            return true;
        };
    }

    return {
        makeExtensionColumn,
        makeDbkeyColumn,
    };
}
