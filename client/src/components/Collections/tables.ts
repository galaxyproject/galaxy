import { computed, ref } from "vue";

export function useTableSummary() {
    const rawValue = ref<string>("");

    const table = computed(() => {
        return rawToTable(rawValue.value);
    });

    const columnCount = computed<number>(() => {
        const tableVal = table.value;
        if (tableVal && tableVal.length) {
            return tableVal[0]?.length || 0;
        } else {
            return 0;
        }
    });

    const isJaggedData = computed<boolean>(() => {
        const tableVal = table.value;
        const columnCountVal = columnCount.value;
        for (const row of tableVal) {
            if (row.length != columnCountVal) {
                return true;
            }
        }
        return false;
    });

    const jaggedDataWarning = computed<string | undefined>(() => {
        if (isJaggedData.value) {
            return "This data contains a different number of columns per-row, this probably shouldn't be used as is.";
        } else {
            return undefined;
        }
    });
    return {
        rawValue,
        isJaggedData,
        jaggedDataWarning,
        columnCount,
        table,
    };
}

export function rawToTable(content: string): string[][] {
    const hasNonWhitespaceChars = RegExp(/[^\s]/);
    // Have pasted data, data from a history dataset, or FTP list.
    const lines = content.split(/[\n\r]/).filter((line) => line.length > 0 && hasNonWhitespaceChars.exec(line));
    // Really poor tabular parser - we should get a library for this or expose options? I'm not
    // sure.
    let hasTabs = false;
    if (lines.length > 0) {
        const firstLine = lines[0];
        if (firstLine && firstLine.indexOf("\t") >= 0) {
            hasTabs = true;
        }
    }
    const regex = hasTabs ? /\t/ : /\s+/;
    return lines.map((line) => line.split(regex));
}
