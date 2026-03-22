#!/usr/bin/env python3
"""
Refresh section-derived tool tags from the Galaxy EU tools API.
"""
import json
import re
from pathlib import Path
import urllib.request

import yaml
from yaml.events import (
    AliasEvent,
    CollectionStartEvent,
    NodeEvent,
    ScalarEvent,
)

# API endpoint
API_URL = "https://usegalaxy.eu/api/tools/"

# Output file
OUTPUT_FILE = Path("lib/galaxy/tool_util/ontologies/tool_tag_mappings.yml")
SAFE_UNQUOTED_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
YAML_BOOLEAN_LIKE_VALUES = {"", "~", "null", "Null", "NULL", "true", "True", "TRUE", "false", "False", "FALSE"}


class QuotedString(str):
    """Marker type for YAML strings that must be emitted with quotes."""


class QuotingDumper(yaml.SafeDumper):
    """YAML dumper that keeps our scalar quoting explicit and predictable."""

    def check_simple_key(self):
        length = 0
        if isinstance(self.event, NodeEvent) and self.event.anchor is not None:
            if self.prepared_anchor is None:
                self.prepared_anchor = self.prepare_anchor(self.event.anchor)
            length += len(self.prepared_anchor)
        if isinstance(self.event, (ScalarEvent, CollectionStartEvent)) and self.event.tag is not None:
            if self.prepared_tag is None:
                self.prepared_tag = self.prepare_tag(self.event.tag)
            length += len(self.prepared_tag)
        if isinstance(self.event, ScalarEvent):
            if self.analysis is None:
                self.analysis = self.analyze_scalar(self.event.value)
            length += len(self.analysis.scalar)
        return (
            length < 4096
            and (
                isinstance(self.event, AliasEvent)
                or (isinstance(self.event, ScalarEvent) and not self.analysis.empty and not self.analysis.multiline)
                or self.check_empty_sequence()
                or self.check_empty_mapping()
            )
        )


def represent_quoted_string(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


QuotingDumper.add_representer(QuotedString, represent_quoted_string)


def fetch_tools():
    """Fetch tools from Galaxy EU API"""
    print(f"Fetching tools from {API_URL}...")
    try:
        with urllib.request.urlopen(API_URL) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def normalize_section_alias(value):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def tool_id_candidates(tool_id):
    candidates = [tool_id]
    if tool_id.startswith("toolshed.") and tool_id.count("/") >= 5:
        short_id = tool_id.rsplit("/", 1)[0]
        if short_id not in candidates:
            candidates.append(short_id)
    return candidates


def extract_sections_and_tools(data):
    """Extract ToolSections and their tools from API response."""
    sections = {}
    section_ids = {}

    for item in data:
        if item.get("model_class") == "ToolSection":
            section_id = item.get("id")
            section_name = item.get("name")
            if section_id and section_name:
                section_ids[section_id] = section_name
            print(f"Found section: {section_name} (id: {section_id})")

            # Extract tools in this section
            tools = []
            for elem in item.get("elems", []):
                model_class = elem.get("model_class", "")
                if isinstance(model_class, str) and model_class.endswith("Tool"):
                    tool_id = elem.get("id")
                    if tool_id:
                        for candidate in tool_id_candidates(tool_id):
                            if candidate not in tools:
                                tools.append(candidate)

            if tools:
                sections.setdefault(section_name, []).extend(tools)
                print(f"  - Contains {len(tools)} tools")

    return sections, section_ids


def load_existing_mappings():
    """Load existing tool_tag_mappings.yml"""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"tool_tags": {}}


def normalize_tool_tags(tool_tags):
    normalized = {}
    for tool_id, tags in tool_tags.items():
        unique_tags = []
        for tag in tags:
            if tag not in unique_tags:
                unique_tags.append(tag)
        normalized[tool_id] = unique_tags
    return normalized


def validate_mappings_data(data):
    tool_tags = data.get("tool_tags", {})
    if not isinstance(tool_tags, dict):
        raise ValueError("tool_tag_mappings.yml must contain a top-level 'tool_tags' mapping.")
    for tool_id, tags in tool_tags.items():
        if not isinstance(tool_id, str):
            raise ValueError(f"Tool id {tool_id!r} must be a string.")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"Tags for tool {tool_id!r} must be a list of strings.")
    return {"tool_tags": normalize_tool_tags(tool_tags)}


def needs_quotes(value):
    return value in YAML_BOOLEAN_LIKE_VALUES or not SAFE_UNQUOTED_RE.fullmatch(value)


def prepare_for_dump(value):
    if isinstance(value, dict):
        return {prepare_for_dump(key): prepare_for_dump(item) for key, item in value.items()}
    if isinstance(value, list):
        return [prepare_for_dump(item) for item in value]
    if isinstance(value, str) and needs_quotes(value):
        return QuotedString(value)
    return value


def update_mappings(existing_data, sections, section_ids):
    """Refresh section tags while preserving existing non-section curated tags."""
    section_aliases = {normalize_section_alias(alias) for alias in set(section_ids) | set(section_ids.values())}
    tool_tags = {}

    for tool_id, tags in existing_data.get("tool_tags", {}).items():
        custom_tags = [tag for tag in tags if normalize_section_alias(tag) not in section_aliases]
        if custom_tags:
            tool_tags[tool_id] = custom_tags

    # Track statistics
    new_mappings = 0
    updated_mappings = 0

    for section_name, tools in sections.items():
        tag = section_name

        for tool_id in tools:
            if tool_id in tool_tags:
                # Check if tag already exists
                if tag not in tool_tags[tool_id]:
                    tool_tags[tool_id].append(tag)
                    updated_mappings += 1
                    print(f"  Updated {tool_id} with tag: {tag}")
            else:
                tool_tags[tool_id] = [tag]
                new_mappings += 1
                print(f"  Added {tool_id} with tag: {tag}")

    print(f"\nSummary:")
    print(f"  - New tool mappings: {new_mappings}")
    print(f"  - Updated tool mappings: {updated_mappings}")
    print(f"  - Total tools with tags: {len(tool_tags)}")

    return {"tool_tags": normalize_tool_tags(tool_tags)}


def save_mappings(data):
    """Save updated tool_tag_mappings.yml"""
    validated_data = validate_mappings_data(data)
    serialized = yaml.dump(
        prepare_for_dump(validated_data),
        Dumper=QuotingDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )

    # Validate that the serialized YAML round-trips cleanly.
    round_trip = yaml.safe_load(serialized)
    if round_trip != validated_data:
        raise ValueError("Serialized YAML did not round-trip correctly.")

    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(serialized)
    print("Done!")


def main():
    # Fetch tools from API
    data = fetch_tools()
    if not data:
        return

    # Extract sections and tools
    sections, section_ids = extract_sections_and_tools(data)
    if not sections:
        print("No sections found!")
        return

    # Load existing mappings
    existing_data = load_existing_mappings()

    # Update mappings
    updated_data = update_mappings(existing_data, sections, section_ids)

    # Save mappings
    save_mappings(updated_data)


if __name__ == "__main__":
    main()
