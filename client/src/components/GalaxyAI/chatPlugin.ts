/** Galaxy sends the chat plugin `galaxy` events; the plugin reports `galaxy-visualization` events. */

const CHAT_VIEW = "chat";

interface ChatConfig {
    view: typeof CHAT_VIEW;
    exchange_id?: string;
    question?: string;
}

export type ChatCommand = { type: "open"; exchange_id: string } | { type: "ask"; question: string };

export function chatConfig(command?: ChatCommand): ChatConfig {
    const config: ChatConfig = { view: CHAT_VIEW };
    if (command?.type === "open") {
        config.exchange_id = command.exchange_id;
    } else if (command?.type === "ask") {
        config.question = command.question;
    }
    return config;
}

export function commandMessage(command: ChatCommand) {
    return { from: "galaxy", ...command };
}

export function activeChat(config: unknown): string | null | undefined {
    const id = (config as Record<string, unknown> | null)?.exchange_id;
    return id === null || (typeof id === "string" && id) ? id : undefined;
}

export function importPlugin(url: string) {
    return import(/* @vite-ignore */ url);
}

export function hasAiChat(config?: { ai_chat_plugin?: string | null; llm_api_configured?: boolean }): boolean {
    return Boolean(config?.ai_chat_plugin || config?.llm_api_configured);
}
