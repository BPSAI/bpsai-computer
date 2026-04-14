"""Portfolio YAML indexer for episodic retrieval.

Extracts meaningful text from portfolio YAML documents (decisions,
hypotheses, strategy) into chunks suitable for EpisodicIndex.build().
Each chunk carries source path, document type, and document ID metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PortfolioChunk:
    """A text chunk extracted from a portfolio YAML document."""

    text: str
    source_path: str
    doc_type: str
    doc_id: str


# Fields to extract text from, grouped by document type.
_TEXT_FIELDS: dict[str, list[str]] = {
    "decision": ["title", "decision", "reasoning"],
    "hypothesis": ["title", "pattern", "current_signal", "instrumentation_needed"],
}


def _detect_doc_type(doc_id: str) -> str:
    """Infer document type from the ID prefix."""
    if doc_id.startswith("D-"):
        return "decision"
    if doc_id.startswith("HYP-"):
        return "hypothesis"
    return "unknown"


def extract_chunks_from_yaml(path: Path) -> list[PortfolioChunk]:
    """Extract text chunks from a portfolio YAML file.

    Reads structured fields (title, decision, reasoning, pattern, etc.)
    and produces one chunk per non-empty field.

    Args:
        path: Path to a YAML file with an 'id' field.

    Returns:
        List of PortfolioChunk with metadata.
    """
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "id" not in data:
        return []

    doc_id = str(data["id"])
    doc_type = _detect_doc_type(doc_id)
    fields = _TEXT_FIELDS.get(doc_type, ["title"])
    source = str(path)

    chunks: list[PortfolioChunk] = []
    for field in fields:
        value = data.get(field)
        if value and isinstance(value, str) and value.strip():
            chunks.append(PortfolioChunk(
                text=value.strip(),
                source_path=source,
                doc_type=doc_type,
                doc_id=doc_id,
            ))
    return chunks


def extract_chunks_from_directory(dir_path: Path) -> list[PortfolioChunk]:
    """Walk a directory and extract chunks from all YAML files.

    Silently skips files that fail to parse.

    Args:
        dir_path: Root directory to scan for .yaml files.

    Returns:
        Combined list of PortfolioChunk from all valid YAML files.
    """
    chunks: list[PortfolioChunk] = []
    for file_path in sorted(dir_path.rglob("*.yaml")):
        if not file_path.is_file():
            continue
        try:
            chunks.extend(extract_chunks_from_yaml(file_path))
        except (yaml.YAMLError, OSError):
            continue
    return chunks


def prepare_for_episodic_index(
    chunks: list[PortfolioChunk],
) -> list[dict[str, str]]:
    """Convert PortfolioChunks to the format EpisodicIndex.build() expects.

    Each output dict has 'text' and 'source' keys. The source encodes
    document type and ID for traceability.

    Args:
        chunks: List of PortfolioChunk to convert.

    Returns:
        List of dicts with 'text' and 'source' keys.
    """
    return [
        {
            "text": chunk.text,
            "source": f"{chunk.doc_type}:{chunk.doc_id}:{chunk.source_path}",
        }
        for chunk in chunks
    ]
