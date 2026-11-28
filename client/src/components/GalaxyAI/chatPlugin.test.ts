import { describe, expect, it } from "vitest";

import { activeChat, chatConfig, commandMessage, hasAiChat } from "./chatPlugin";

describe("the chat plugin contract", () => {
    it("reads the chat a reported config names", () => {
        expect(activeChat({ exchange_id: "a1" })).toBe("a1");
        expect(activeChat({ exchange_id: null })).toBeNull();
    });

    it("reads no chat from other configs", () => {
        expect(activeChat(null)).toBeUndefined();
        expect(activeChat({})).toBeUndefined();
        expect(activeChat({ exchange_id: "" })).toBeUndefined();
        expect(activeChat({ exchange_id: 7 })).toBeUndefined();
        expect(activeChat({ question: "Hi" })).toBeUndefined();
    });

    it("marks the commands Galaxy sends", () => {
        expect(commandMessage({ type: "ask", question: "Hi" })).toEqual({
            from: "galaxy",
            type: "ask",
            question: "Hi",
        });
    });

    it("mounts the plugin with the first command it is given", () => {
        expect(chatConfig()).toEqual({ view: "chat" });
        expect(chatConfig({ type: "open", exchange_id: "a1" })).toEqual({ view: "chat", exchange_id: "a1" });
        expect(chatConfig({ type: "ask", question: "Hi" })).toEqual({ view: "chat", question: "Hi" });
    });

    it("offers the chat with a plugin or with Galaxy's own AI", () => {
        expect(hasAiChat({ ai_chat_plugin: "fixture" })).toBe(true);
        expect(hasAiChat({ llm_api_configured: true })).toBe(true);
        expect(hasAiChat({ llm_api_configured: false, ai_chat_plugin: null })).toBe(false);
        expect(hasAiChat(undefined)).toBe(false);
    });
});
