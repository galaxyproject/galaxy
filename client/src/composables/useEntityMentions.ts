import { isHDA } from "@/api";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";

export type EntityType = "dataset" | "history";

export interface MentionTrigger {
    /** The entity type being selected, or null if still picking a type */
    entityType: EntityType | null;
    /** Text after the entity prefix for filtering (e.g. "foo" from "@dataset:foo") */
    searchText: string;
    /** Character index where the `@` trigger starts */
    startIndex: number;
    /** Character index where the current mention text ends (cursor position) */
    endIndex: number;
}

export interface ParsedMention {
    type: EntityType;
    identifier: string;
    startIndex: number;
    endIndex: number;
}

export interface ResolvedEntity {
    type: EntityType;
    identifier: string;
    id: string | null;
    name: string;
    extension?: string;
    state?: string;
    hid?: number;
}

export const MENTION_PATTERN_SOURCE = "@(dataset|history):(\\S+)";

export function detectMentionTrigger(text: string, cursorPos: number): MentionTrigger | null {
    // Walk backwards from cursor to find the nearest unmatched `@`
    const before = text.slice(0, cursorPos);
    const atIndex = before.lastIndexOf("@");
    if (atIndex === -1) {
        return null;
    }

    // `@` must be at the start of input or preceded by whitespace
    if (atIndex > 0 && !/\s/.test(before[atIndex - 1]!)) {
        return null;
    }

    const fragment = before.slice(atIndex + 1); // text after `@`

    // If there's a space in the fragment, the user has moved past the mention
    if (/\s/.test(fragment)) {
        return null;
    }

    // Check if user has typed an entity prefix like "dataset:" or "history:"
    const prefixMatch = fragment.match(/^(dataset|history):(.*)$/i);
    if (prefixMatch) {
        return {
            entityType: prefixMatch[1]!.toLowerCase() as EntityType,
            searchText: prefixMatch[2]!,
            startIndex: atIndex,
            endIndex: cursorPos,
        };
    }

    // Still typing the entity type name (or just typed `@`)
    return {
        entityType: null,
        searchText: fragment,
        startIndex: atIndex,
        endIndex: cursorPos,
    };
}

export function parseMentions(text: string): ParsedMention[] {
    const mentions: ParsedMention[] = [];
    let match: RegExpExecArray | null;
    const re = new RegExp(MENTION_PATTERN_SOURCE, "g");
    while ((match = re.exec(text)) !== null) {
        mentions.push({
            type: match[1] as EntityType,
            identifier: match[2]!,
            startIndex: match.index,
            endIndex: match.index + match[0].length,
        });
    }
    return mentions;
}

export function resolveMentions(mentions: ParsedMention[]): ResolvedEntity[] {
    const historyStore = useHistoryStore();
    const historyItemsStore = useHistoryItemsStore();
    const historyId = historyStore.currentHistoryId;

    const resolved: ResolvedEntity[] = [];

    for (const mention of mentions) {
        if (mention.type === "dataset" && historyId) {
            const items = historyItemsStore.getHistoryItems(historyId, "");
            const hid = parseInt(mention.identifier, 10);

            const found = !isNaN(hid)
                ? items.find((item) => item.hid === hid)
                : items.find((item) => (item.name ?? "").toLowerCase().includes(mention.identifier.toLowerCase()));

            if (found && isHDA(found)) {
                resolved.push({
                    type: "dataset",
                    identifier: mention.identifier,
                    id: found.id,
                    name: found.name ?? `Dataset ${found.hid}`,
                    extension: found.extension ?? undefined,
                    state: found.state,
                    hid: found.hid,
                });
            } else {
                resolved.push({
                    type: "dataset",
                    identifier: mention.identifier,
                    id: null,
                    name: `Dataset ${mention.identifier}`,
                });
            }
        } else if (mention.type === "history") {
            if (mention.identifier === "current") {
                const current = historyStore.currentHistory;
                if (current) {
                    resolved.push({
                        type: "history",
                        identifier: "current",
                        id: current.id,
                        name: current.name,
                    });
                }
            } else {
                const hist = historyStore.getHistoryById(mention.identifier);
                if (hist) {
                    resolved.push({
                        type: "history",
                        identifier: mention.identifier,
                        id: hist.id,
                        name: hist.name,
                    });
                }
            }
        }
    }

    return resolved;
}

export function buildEntityContext(entities: ResolvedEntity[]): {
    datasets: ResolvedEntity[];
    histories: ResolvedEntity[];
} | null {
    const datasets = entities.filter((e) => e.type === "dataset");
    const histories = entities.filter((e) => e.type === "history");
    if (datasets.length === 0 && histories.length === 0) {
        return null;
    }
    return { datasets, histories };
}
