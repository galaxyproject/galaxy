#!/usr/bin/env python3
"""
Build GTN Search Database from GTN Repository.

This script processes the Galaxy Training Network repository and creates
a SQLite database with FTS5 full-text search capabilities for fast tutorial search.

Usage:
    python build_database.py <gtn_repo_path> [--output <db_path>]
"""

import json
import logging
import re
import sqlite3
import sys
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import (
    Any,
    Optional,
    Union,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

DB_VERSION = "1.1.0"


@dataclass
class FAQ:
    """Represents a GTN FAQ entry."""

    category: str  # "galaxy" or "gtn"
    filename: str
    title: str
    area: str = ""
    box_type: str = ""
    content: str = ""
    content_hash: str = ""
    last_modified: str = ""
    contributors: list[str] = field(default_factory=list)


@dataclass
class Tutorial:
    """Represents a GTN tutorial with all its metadata."""

    topic: str
    tutorial: str
    title: str
    description: str = ""
    url: str = ""
    difficulty: str = "intermediate"
    hands_on: bool = True
    time_estimation: str = ""
    content: str = ""
    questions: str = ""
    objectives: str = ""
    key_points: str = ""
    tools: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""
    last_modified: str = ""
    gtn_commit: str = ""
    zenodo_link: str = ""
    workflows: list[str] = field(default_factory=list)


class GTNDatabaseBuilder:
    """Builds SQLite database from GTN repository."""

    def __init__(self, gtn_path: Path, output_path: Optional[Path] = None):
        self.gtn_path = gtn_path
        self.output_path = output_path or Path("gtn_search.db")
        self.tutorials: list[Tutorial] = []
        self.faqs: list[FAQ] = []

    def build(self):
        """Build the complete database."""
        log.info(f"Building GTN database from {self.gtn_path}")

        # Collect all tutorials
        self.collect_tutorials()

        # Collect all FAQs
        self.collect_faqs()

        # Create database
        self.create_database()

        # Insert tutorials
        self.insert_tutorials()

        # Insert FAQs
        self.insert_faqs()

        # Add metadata
        self.add_metadata()

        # Optimize database
        self.optimize_database()

        log.info(f"Database built successfully: {self.output_path}")
        log.info(f"Total tutorials indexed: {len(self.tutorials)}")
        log.info(f"Total FAQs indexed: {len(self.faqs)}")

    def collect_tutorials(self):
        """Collect all tutorials from the GTN repository."""
        topics_dir = self.gtn_path / "topics"

        if not topics_dir.exists():
            raise ValueError(f"Topics directory not found: {topics_dir}")

        # Iterate through all topics
        for topic_dir in topics_dir.iterdir():
            if not topic_dir.is_dir() or topic_dir.name.startswith("."):
                continue

            topic = topic_dir.name
            tutorials_dir = topic_dir / "tutorials"

            if not tutorials_dir.exists():
                continue

            # Iterate through tutorials in this topic
            for tutorial_dir in tutorials_dir.iterdir():
                if not tutorial_dir.is_dir():
                    continue

                tutorial_name = tutorial_dir.name
                tutorial_file = tutorial_dir / "tutorial.md"

                if tutorial_file.exists():
                    try:
                        tutorial = self.parse_tutorial(tutorial_file, topic, tutorial_name)
                        if tutorial:
                            self.tutorials.append(tutorial)
                            log.debug(f"Parsed tutorial: {topic}/{tutorial_name}")
                    except (OSError, ValueError, KeyError) as e:
                        log.warning(f"Failed to parse {topic}/{tutorial_name}: {e}")

    def collect_faqs(self):
        """Collect all FAQs from the GTN repository."""
        faqs_dir = self.gtn_path / "faqs"

        if not faqs_dir.exists():
            log.warning(f"FAQs directory not found: {faqs_dir}")
            return

        # Process Galaxy FAQs
        galaxy_faqs_dir = faqs_dir / "galaxy"
        if galaxy_faqs_dir.exists():
            for faq_file in galaxy_faqs_dir.glob("*.md"):
                if faq_file.name != "index.md":
                    try:
                        faq = self.parse_faq(faq_file, "galaxy")
                        if faq:
                            self.faqs.append(faq)
                            log.debug(f"Parsed FAQ: galaxy/{faq_file.name}")
                    except (OSError, ValueError, KeyError) as e:
                        log.warning(f"Failed to parse FAQ galaxy/{faq_file.name}: {e}")

        # Process GTN FAQs
        gtn_faqs_dir = faqs_dir / "gtn"
        if gtn_faqs_dir.exists():
            for faq_file in gtn_faqs_dir.glob("*.md"):
                if faq_file.name != "index.md":
                    try:
                        faq = self.parse_faq(faq_file, "gtn")
                        if faq:
                            self.faqs.append(faq)
                            log.debug(f"Parsed FAQ: gtn/{faq_file.name}")
                    except (OSError, ValueError, KeyError) as e:
                        log.warning(f"Failed to parse FAQ gtn/{faq_file.name}: {e}")

    def parse_faq(self, faq_file: Path, category: str) -> Optional[FAQ]:
        """Parse a FAQ markdown file, returning None on failure."""
        try:
            with open(faq_file, encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            frontmatter = {}
            if content.startswith("---"):
                try:
                    end_index = content.index("---", 3)
                    yaml_content = content[3:end_index]
                    frontmatter = self.parse_yaml_simple(yaml_content)
                    # Remove frontmatter from content
                    content = content[end_index + 3 :].strip()
                except ValueError:
                    pass

            # Get file stats
            stat = faq_file.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Calculate content hash
            content_bytes = content.encode("utf-8")
            content_hash = md5(content_bytes).hexdigest()

            # Extract contributors list if present
            contributors = []
            if "contributors" in frontmatter:
                contrib_value = frontmatter["contributors"]
                if isinstance(contrib_value, str):
                    # Parse the string that looks like "[user1, user2]"
                    contrib_str = contrib_value.strip("[]")
                    contributors = [c.strip() for c in contrib_str.split(",")]
                elif isinstance(contrib_value, list):
                    contributors = contrib_value

            # Create FAQ object
            faq = FAQ(
                category=category,
                filename=faq_file.stem,  # filename without .md extension
                title=frontmatter.get("title", faq_file.stem.replace("-", " ").title()),
                area=frontmatter.get("area", ""),
                box_type=frontmatter.get("box_type", ""),
                content=content,
                content_hash=content_hash,
                last_modified=last_modified,
                contributors=contributors,
            )

            return faq

        except (OSError, ValueError, KeyError) as e:
            log.warning(f"Error parsing FAQ {faq_file}: {e}")
            return None

    def parse_tutorial(self, tutorial_file: Path, topic: str, tutorial_name: str) -> Optional[Tutorial]:
        """Parse a tutorial markdown file, returning None on failure."""
        try:
            with open(tutorial_file, encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter (YAML between --- markers)
            frontmatter = {}
            if content.startswith("---"):
                try:
                    end_index = content.index("---", 3)
                    yaml_content = content[3:end_index]
                    frontmatter = self.parse_yaml_simple(yaml_content)
                    # Remove frontmatter from content
                    content = content[end_index + 3 :].strip()
                except ValueError:
                    pass

            # Extract key sections from content
            questions = self.extract_section(content, "questions")
            objectives = self.extract_section(content, "objectives")
            key_points = self.extract_section(content, "keypoints") or self.extract_section(content, "key_points")

            # Build tutorial URL
            base_url = "https://training.galaxyproject.org/training-material"
            url = f"{base_url}/topics/{topic}/tutorials/{tutorial_name}/tutorial.html"

            # Get file stats
            stat = tutorial_file.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Calculate content hash
            content_bytes = content.encode("utf-8")
            content_hash = md5(content_bytes).hexdigest()

            # Create tutorial object
            tutorial = Tutorial(
                topic=topic,
                tutorial=tutorial_name,
                title=frontmatter.get("title", tutorial_name.replace("-", " ").title()),
                description=frontmatter.get("description", ""),
                url=url,
                difficulty=str(frontmatter.get("level", "intermediate")).lower(),
                hands_on=frontmatter.get("hands_on", True) not in (False, "false", "False"),
                time_estimation=frontmatter.get("time_estimation", ""),
                content=content[:50000],  # Limit content size
                questions=questions,
                objectives=objectives,
                key_points=key_points,
                tools=self.extract_list(frontmatter.get("tools", [])),
                requirements=self.extract_list(frontmatter.get("requirements", [])),
                tags=self.extract_list(frontmatter.get("tags", [])),
                content_hash=content_hash,
                last_modified=last_modified,
                zenodo_link=str(frontmatter.get("zenodo_link", "") or ""),
            )

            return tutorial

        except (OSError, ValueError, KeyError) as e:
            log.warning(f"Error parsing tutorial {tutorial_file}: {e}")
            return None

    def parse_yaml_simple(self, yaml_content: str) -> dict[str, Any]:
        """Simple YAML frontmatter parser (no external dependencies)."""
        result: dict[str, Any] = {}
        current_list: Optional[list[str]] = None

        for line in yaml_content.split("\n"):
            line = line.rstrip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Handle list items
            if line.startswith("  - ") or line.startswith("- "):
                if current_list is not None:
                    item = line.strip("- ").strip()
                    if item:
                        current_list.append(item)
                continue

            # Handle key-value pairs (only top-level keys, not indented)
            if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
                parts = line.split(":", 1)
                key = parts[0].strip()
                str_value = parts[1].strip() if len(parts) > 1 else ""

                # Remove quotes if present
                was_quoted = False
                if str_value.startswith('"') and str_value.endswith('"'):
                    str_value = str_value[1:-1]
                    was_quoted = True
                elif str_value.startswith("'") and str_value.endswith("'"):
                    str_value = str_value[1:-1]
                    was_quoted = True

                # Check for boolean values
                parsed_value: Union[str, bool, list[str]]
                if str_value.lower() == "true":
                    parsed_value = True
                elif str_value.lower() == "false":
                    parsed_value = False
                elif str_value == "" and not was_quoted:
                    # Unquoted empty value — this might be a list header
                    current_list = []
                    result[key] = current_list
                    continue
                else:
                    parsed_value = str_value

                result[key] = parsed_value
                current_list = None

        return result

    def extract_section(self, content: str, section_name: str) -> str:
        """Extract a section from markdown content."""
        escaped = re.escape(section_name)
        patterns = [
            rf"{{:\s*\.{escaped}.*?}}(.*?)(?:{{:|^#|\Z)",
            rf">{{\%\s*icon\s+{escaped}.*?\%}}.*?\n(.*?)(?:^#|\Z)",
            rf"<{escaped}.*?>(.*?)</{escaped}>",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.MULTILINE | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                # Clean up the text
                text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
                text = re.sub(r"{%.*?%}", "", text)
                text = re.sub(r"{:.*?}", "", text)
                return text.strip()[:1000]  # Limit section size

        return ""

    def extract_list(self, value: Any) -> list[str]:
        """Extract a list from various input formats."""
        if isinstance(value, list):
            return [str(item) for item in value]
        elif isinstance(value, str):
            return [value]
        else:
            return []

    def create_database(self):
        """Create the SQLite database with FTS5 tables."""
        if self.output_path.exists():
            self.output_path.unlink()

        with sqlite3.connect(str(self.output_path)) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE tutorials (
                    id INTEGER PRIMARY KEY,
                    topic TEXT NOT NULL,
                    tutorial TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT NOT NULL,
                    difficulty TEXT,
                    hands_on BOOLEAN DEFAULT 1,
                    time_estimation TEXT,
                    content TEXT NOT NULL,
                    questions TEXT,
                    objectives TEXT,
                    key_points TEXT,
                    tools_json TEXT,
                    requirements_json TEXT,
                    tags_json TEXT,
                    content_hash TEXT NOT NULL,
                    last_modified TEXT,
                    gtn_commit TEXT,
                    zenodo_link TEXT,
                    workflows_json TEXT,
                    UNIQUE(topic, tutorial)
                )
            """)

            # FTS5 content tables track the source table automatically
            cursor.execute("""
                CREATE VIRTUAL TABLE tutorials_fts USING fts5(
                    title, description, content, topic,
                    content=tutorials, content_rowid=id,
                    tokenize='porter unicode61'
                )
            """)

            cursor.execute("""
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE example_queries (
                    id INTEGER PRIMARY KEY,
                    query TEXT NOT NULL,
                    description TEXT,
                    category TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE faqs (
                    id INTEGER PRIMARY KEY,
                    category TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    title TEXT NOT NULL,
                    area TEXT,
                    box_type TEXT,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    last_modified TEXT,
                    contributors_json TEXT,
                    UNIQUE(category, filename)
                )
            """)

            cursor.execute("""
                CREATE VIRTUAL TABLE faqs_fts USING fts5(
                    title, content, category, area,
                    content=faqs, content_rowid=id,
                    tokenize='porter unicode61'
                )
            """)

            cursor.execute("CREATE INDEX idx_topic_difficulty ON tutorials(topic, difficulty)")
            cursor.execute("CREATE INDEX idx_hands_on ON tutorials(hands_on)")
            cursor.execute("CREATE INDEX idx_content_hash ON tutorials(content_hash)")
            cursor.execute("CREATE INDEX idx_faq_category ON faqs(category)")
            cursor.execute("CREATE INDEX idx_faq_area ON faqs(area)")

            conn.commit()

    def insert_tutorials(self):
        """Insert tutorials into the database."""
        with sqlite3.connect(str(self.output_path)) as conn:
            cursor = conn.cursor()

            for tutorial in self.tutorials:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO tutorials (
                            topic, tutorial, title, description, url, difficulty,
                            hands_on, time_estimation, content, questions, objectives,
                            key_points, tools_json, requirements_json, tags_json,
                            content_hash, last_modified, gtn_commit, zenodo_link, workflows_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            tutorial.topic,
                            tutorial.tutorial,
                            tutorial.title,
                            tutorial.description,
                            tutorial.url,
                            tutorial.difficulty,
                            int(tutorial.hands_on),
                            tutorial.time_estimation,
                            tutorial.content,
                            tutorial.questions,
                            tutorial.objectives,
                            tutorial.key_points,
                            json.dumps(tutorial.tools),
                            json.dumps(tutorial.requirements),
                            json.dumps(tutorial.tags),
                            tutorial.content_hash,
                            tutorial.last_modified,
                            tutorial.gtn_commit,
                            tutorial.zenodo_link,
                            json.dumps(tutorial.workflows),
                        ),
                    )
                except (sqlite3.Error, ValueError, TypeError) as e:
                    log.warning(f"Failed to insert tutorial {tutorial.topic}/{tutorial.tutorial}: {e}")

            # Rebuild FTS index from content table
            cursor.execute("INSERT INTO tutorials_fts(tutorials_fts) VALUES('rebuild')")
            conn.commit()

    def insert_faqs(self):
        """Insert FAQs into the database."""
        with sqlite3.connect(str(self.output_path)) as conn:
            cursor = conn.cursor()

            for faq in self.faqs:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO faqs (
                            category, filename, title, area, box_type,
                            content, content_hash, last_modified, contributors_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            faq.category,
                            faq.filename,
                            faq.title,
                            faq.area,
                            faq.box_type,
                            faq.content,
                            faq.content_hash,
                            faq.last_modified,
                            json.dumps(faq.contributors),
                        ),
                    )
                except (sqlite3.Error, ValueError, TypeError) as e:
                    log.warning(f"Failed to insert FAQ {faq.category}/{faq.filename}: {e}")

            # Rebuild FTS index from content table
            cursor.execute("INSERT INTO faqs_fts(faqs_fts) VALUES('rebuild')")
            conn.commit()

    def add_metadata(self):
        """Add metadata to the database."""
        with sqlite3.connect(str(self.output_path)) as conn:
            cursor = conn.cursor()

            metadata = {
                "version": DB_VERSION,
                "build_date": datetime.now().isoformat(),
                "tutorial_count": str(len(self.tutorials)),
                "faq_count": str(len(self.faqs)),
                "gtn_repository": "https://github.com/galaxyproject/training-material",
                "builder_version": DB_VERSION,
            }

            for key, value in metadata.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    (key, value),
                )

            example_queries = [
                ("RNA-seq", "Find RNA sequencing tutorials", "analysis"),
                ("differential expression", "Tutorials on differential expression analysis", "analysis"),
                ("quality control", "QC and data preprocessing tutorials", "preprocessing"),
                ("workflow", "Workflow creation and management", "galaxy"),
                ("beginner", "Tutorials for beginners", "skill-level"),
                ("tool development", "Creating custom Galaxy tools", "development"),
            ]

            for query, description, category in example_queries:
                cursor.execute(
                    "INSERT INTO example_queries (query, description, category) VALUES (?, ?, ?)",
                    (query, description, category),
                )

            conn.commit()

    def optimize_database(self):
        """Optimize the database for size and performance."""
        with sqlite3.connect(str(self.output_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tutorials_fts(tutorials_fts) VALUES('optimize')")
            cursor.execute("INSERT INTO faqs_fts(faqs_fts) VALUES('optimize')")
            cursor.execute("ANALYZE")
            conn.commit()

        # VACUUM must run outside a transaction
        with sqlite3.connect(str(self.output_path)) as conn:
            conn.execute("VACUUM")


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Build GTN Search Database from GTN Repository")
    parser.add_argument("gtn_repo_path", type=str, help="Path to cloned GTN repository")
    parser.add_argument("--output", type=str, help="Output database path (default: gtn_search.db)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    gtn_path = Path(args.gtn_repo_path)
    output_path = Path(args.output) if args.output else None

    if not gtn_path.exists():
        log.error(f"GTN repository path does not exist: {gtn_path}")
        sys.exit(1)

    try:
        builder = GTNDatabaseBuilder(gtn_path, output_path)
        builder.build()

        # Print database statistics
        output_path = builder.output_path
        size_mb = output_path.stat().st_size / (1024 * 1024)
        log.info(f"Database size: {size_mb:.2f} MB")

    except Exception as e:
        log.error(f"Failed to build database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
