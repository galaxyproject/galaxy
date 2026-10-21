import { faMagic, faRobot } from "@fortawesome/free-solid-svg-icons";
import { describe, expect, it } from "vitest";

import type { AgentResponse } from "@/composables/agentActions";

import { formatModelName, getAgentIcon, getAgentLabel, getAgentResponseOrEmpty } from "./agentTypes";

describe("agentTypes", () => {
    describe("getAgentIcon", () => {
        it("returns the agent's icon for a known agent type", () => {
            expect(getAgentIcon("auto")).toBe(faMagic);
        });

        it.each([
            ["an unknown agent type", "nonexistent"],
            ["undefined", undefined],
            ["an empty string", ""],
        ])("falls back to the robot icon for %s", (_condition, agentType) => {
            expect(getAgentIcon(agentType)).toBe(faRobot);
        });
    });

    describe("getAgentLabel", () => {
        it.each([
            ["auto", "Auto (Router)"],
            ["error_analysis", "Error Analysis"],
            ["gtn_training", "GTN Training"],
        ])("returns the label of known agent type %s", (agentType, label) => {
            expect(getAgentLabel(agentType)).toBe(label);
        });

        it("returns the raw value for an unknown agent type", () => {
            expect(getAgentLabel("my_custom_agent")).toBe("my_custom_agent");
        });

        it.each([
            ["undefined", undefined],
            ["an empty string", ""],
        ])("returns 'AI Assistant' for %s", (_condition, agentType) => {
            expect(getAgentLabel(agentType)).toBe("AI Assistant");
        });
    });

    describe("formatModelName", () => {
        it.each([
            ["keeps the last segment of a provider/model name", "openai/gpt-4", "gpt-4"],
            ["keeps the last segment of a provider/model name", "anthropic/claude-3-opus", "claude-3-opus"],
            ["keeps the last segment of a multi-slash model path", "org/team/gpt-4", "gpt-4"],
            ["returns a name without slashes as-is", "gpt-4", "gpt-4"],
            ["returns the whole name when it ends in a slash", "openai/", "openai/"],
            ["returns an empty string for undefined", undefined, ""],
            ["returns an empty string for an empty string", "", ""],
        ])("%s (%s)", (_behavior, model, formatted) => {
            expect(formatModelName(model)).toBe(formatted);
        });
    });

    describe("getAgentResponseOrEmpty", () => {
        it("returns the provided response when present", () => {
            const response: AgentResponse = {
                content: "hello",
                agent_type: "auto",
                confidence: "high",
                suggestions: [],
                metadata: { model: "gpt-4" },
            };

            expect(getAgentResponseOrEmpty(response)).toBe(response);
        });

        it("returns an empty low-confidence response for undefined", () => {
            expect(getAgentResponseOrEmpty(undefined)).toEqual({
                content: "",
                agent_type: "",
                confidence: "low",
                suggestions: [],
                metadata: {},
            });
        });
    });
});
