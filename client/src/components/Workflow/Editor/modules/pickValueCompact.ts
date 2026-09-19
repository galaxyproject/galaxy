import type { WorkflowConnectionStore } from "@/stores/workflowConnectionStore";
import { getTerminalId } from "@/stores/workflowConnectionStore";
import type { Connection, InputTerminal } from "@/stores/workflowStoreTypes";

export interface CompactRename {
    from: string;
    to: string;
}

export interface CompactResult {
    renames: CompactRename[];
}

/**
 * Compute which terminals need renaming after a disconnect.
 * disconnectedName is excluded from the connected set.
 */
export function computePickValueCompaction(
    inputConnections: Record<string, unknown>,
    disconnectedName: string,
): CompactResult {
    const connected = Object.keys(inputConnections)
        .filter((k) => k.startsWith("input_") && k !== disconnectedName && inputConnections[k] != null)
        .map((k) => ({ name: k, index: parseInt(k.replace("input_", ""), 10) }))
        .sort((a, b) => a.index - b.index);

    const renames: CompactRename[] = [];
    connected.forEach((entry, seqIndex) => {
        if (entry.index !== seqIndex) {
            renames.push({ from: entry.name, to: `input_${seqIndex}` });
        }
    });

    return { renames };
}

/**
 * Apply compaction: rename connections in stores (low to high order).
 */
export function applyCompaction(
    stepId: number,
    renames: CompactRename[],
    connectionStore: WorkflowConnectionStore,
): void {
    for (const rename of renames) {
        const terminalId = getTerminalId({ stepId, name: rename.from, connectorType: "input" });
        const conns = [...connectionStore.getConnectionsForTerminal(terminalId)];

        connectionStore.removeConnection({ stepId, name: rename.from, connectorType: "input" } as InputTerminal);

        for (const conn of conns) {
            const newConn: Connection = {
                input: { stepId, name: rename.to, connectorType: "input" },
                output: { ...conn.output },
            };
            connectionStore.addConnection(newConn);
        }
    }
}

/**
 * Reverse compaction: rename connections back (high to low order).
 */
export function reverseCompaction(
    stepId: number,
    renames: CompactRename[],
    connectionStore: WorkflowConnectionStore,
): void {
    for (const rename of [...renames].reverse()) {
        const terminalId = getTerminalId({ stepId, name: rename.to, connectorType: "input" });
        const conns = [...connectionStore.getConnectionsForTerminal(terminalId)];

        connectionStore.removeConnection({ stepId, name: rename.to, connectorType: "input" } as InputTerminal);

        for (const conn of conns) {
            const newConn: Connection = {
                input: { stepId, name: rename.from, connectorType: "input" },
                output: { ...conn.output },
            };
            connectionStore.addConnection(newConn);
        }
    }
}
