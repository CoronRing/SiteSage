from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:  # Optional dependency; map tools can operate without the OpenAI SDK.
    from openai import OpenAI
except Exception:  # pragma: no cover - defensive import
    OpenAI = None  # type: ignore[assignment]

__all__ = [
    "TypeProjectionAdapter",
    "LLMTypeProjectionAdapter",
    "AMapTaxonomy",
    "AMapTaxonomyEntry",
    "GooglePlacesTaxonomy",
    "GooglePlacesTypeProjectionAdapter",
]

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "data" / "Amap-cls-description.csv"
_PROMPT_CACHE: Dict[str, str] = {}

class TypeProjectionAdapter:
    """Abstract adapter that maps descriptive place types into provider-specific codes."""

    def project_types(self, provider: str, descriptions: Sequence[str]) -> Sequence[str]:
        raise NotImplementedError


def _load_prompt_template(filename: str) -> str:
    if filename in _PROMPT_CACHE:
        return _PROMPT_CACHE[filename]
    path = _PROMPTS_DIR / filename
    text = path.read_text(encoding="utf-8").strip()
    _PROMPT_CACHE[filename] = text
    return text


@dataclass(frozen=True)
class AMapTaxonomyEntry:
    type_code: str
    big_category: str
    mid_category: str
    sub_category: str

    def format_hierarchy(self) -> str:
        hierarchy = " > ".join(
            part for part in (self.big_category, self.mid_category, self.sub_category) if part
        )
        return f"{self.type_code} • {hierarchy}"


class AMapTaxonomy:
    """Loads the AMap classification taxonomy from a CSV export."""

    def __init__(self):
        self.csv_path = _DEFAULT_TAXONOMY_PATH
        self.entries: List[AMapTaxonomyEntry] = []
        self._lookup: Dict[str, AMapTaxonomyEntry] = {}
        self._load()

    def lookup_code(self, label: str) -> Optional[str]:
        if not label:
            return None
        key = _normalize_label(label)
        if not key:
            return None
        entry = self._lookup.get(key)
        return entry.type_code if entry else None

    def prompt_context(self) -> str:
        snippet = (entry.format_hierarchy() for entry in self.entries)
        return "\n".join(snippet)

    def _load(self) -> None:
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                type_code = _clean_cell(row.get("NEW_TYPE"))
                if not type_code:
                    continue
                big = _clean_cell(row.get("Big Category") or row.get("大类"))
                mid = _clean_cell(row.get("Mid Category") or row.get("中类"))
                sub = _clean_cell(row.get("Sub Category") or row.get("小类"))
                entry = AMapTaxonomyEntry(type_code, big, mid, sub)
                self.entries.append(entry)
                labels = [
                    big,
                    mid,
                    sub
                ]
                for label in labels:
                    key = _normalize_label(label)
                    if key:
                        self._lookup.setdefault(key, entry)


class AMapTypeProjectionAdapter(TypeProjectionAdapter):
    """LLM-backed adapter that converts free-form categories into AMap map type codes."""

    def __init__(
        self,
        client: Optional[Any] = None,
        model: str = "gpt-4o-mini"
    ):
        self.taxonomy = AMapTaxonomy()
        self.taxonomy_context = self.taxonomy.prompt_context()
        template = _load_prompt_template("amap_type_projection.txt")
        self.system_prompt = template.format(taxonomy_context=self.taxonomy_context)

        self.model = model
        if client:
            self.client = client
        else:
            self.client = OpenAI()

    def project_types(self, descriptions: Sequence[str]) -> Sequence[str]:
        if not descriptions:
            return []
        descriptions = [desc.strip() for desc in descriptions if desc and desc.strip()]
        
        # matches: the descriptor exactly matches with taxonomy
        # pending: the descriptor does not match with any keys, will use llm to determine
        matches: List[str] = []
        pending: List[str] = []
        for descriptor in descriptions:
            code = self.taxonomy.lookup_code(descriptor)
            if code:
                matches.append(code)
            else:
                pending.append(descriptor)

        if pending:
            for desc in pending:
                matches.extend(self._project_with_llm(desc))

        # deduplicate
        return list(set(matches))

    def _project_with_llm(self, descriptor: str) -> List[str]:
        response = self._invoke_llm(self.system_prompt, descriptor)
        try:
            data = _parse_json(response)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive parsing
            raise RuntimeError("LLM returned invalid JSON for type projection:" + response) from exc

        codes: List[str] = []
        for item in data:
            codes.append(item.get("typecode").strip())

        return codes

    def _invoke_llm(self, system_prompt: str, user_prompt: str) -> str:
        # response api
        if hasattr(self.client, "responses"):
            completion = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt
            )
            return completion.output_text
        # chat api
        elif hasattr(self.client, "chat"):
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return completion.choices[0].message.content or ""
        # raise error if no matching api
        raise RuntimeError("Configured client does not expose a supported API surface.")


class GooglePlacesTaxonomy:
    """Loads Google Places types from CSV."""

    def __init__(self):
        self.csv_path = Path(__file__).resolve().parent / "google_api_utils" / "google_places_types.csv"
        self.types: List[str] = []
        self._lookup: Dict[str, str] = {}
        self._load()

    def lookup_type(self, label: str) -> Optional[str]:
        if not label:
            return None
        key = _normalize_label(label)
        if not key:
            return None
        return self._lookup.get(key)

    def prompt_context(self) -> str:
        return "\n".join(self.types)

    def _load(self) -> None:
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                place_type = _clean_cell(row.get("place_type"))
                if not place_type:
                    continue
                self.types.append(place_type)
                key = _normalize_label(place_type)
                if key:
                    self._lookup[key] = place_type


class GooglePlacesTypeProjectionAdapter(TypeProjectionAdapter):
    """LLM-backed adapter that converts free-form categories into Google Places types."""

    def __init__(
        self,
        client: Optional[Any] = None,
        model: str = "gpt-4o-mini"
    ):
        self.taxonomy = GooglePlacesTaxonomy()
        self.taxonomy_context = self.taxonomy.prompt_context()
        template = _load_prompt_template("google_places_type_projection.txt")
        self.system_prompt = template.format(taxonomy_context=self.taxonomy_context)

        self.model = model
        if client:
            self.client = client
        else:
            self.client = OpenAI()

    def project_types(self, descriptions: Sequence[str]) -> Sequence[str]:
        if not descriptions:
            return []
        descriptions = [desc.strip() for desc in descriptions if desc and desc.strip()]
        
        # matches: the descriptor exactly matches with taxonomy
        # pending: the descriptor does not match with any keys, will use llm to determine
        matches: List[str] = []
        pending: List[str] = []
        for descriptor in descriptions:
            place_type = self.taxonomy.lookup_type(descriptor)
            if place_type:
                matches.append(place_type)
            else:
                pending.append(descriptor)

        if pending:
            for desc in pending:
                matches.extend(self._project_with_llm(desc))

        # deduplicate
        return list(set(matches))

    def _project_with_llm(self, descriptor: str) -> List[str]:
        response = self._invoke_llm(self.system_prompt, descriptor)
        try:
            data = _parse_json(response)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive parsing
            raise RuntimeError("LLM returned invalid JSON for type projection:" + response) from exc

        types: List[str] = []
        for item in data:
            types.append(item.get("place_type").strip())

        return types

    def _invoke_llm(self, system_prompt: str, user_prompt: str) -> str:
        # response api
        if hasattr(self.client, "responses"):
            completion = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt
            )
            return completion.output_text
        # chat api
        elif hasattr(self.client, "chat"):
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return completion.choices[0].message.content or ""
        # raise error if no matching api
        raise RuntimeError("Configured client does not expose a supported API surface.")


def _normalize_label(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _clean_cell(value: Optional[str]) -> str:
    return value.strip() if isinstance(value, str) else ""

def _parse_json(value: str) -> Sequence[Any]:
    idx1 = value.find('[')
    idx2 = len(value) - value[::-1].find(']')
    data = json.loads(value[idx1:idx2])
    return data

