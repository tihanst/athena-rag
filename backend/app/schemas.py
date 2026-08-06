from typing import Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = []


class ChatResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class FileRecord(BaseModel):
    id: str
    name: str
    size: int
    status: Literal["uploading", "ready", "error"] = "ready"


#### For LLM-assisted FTS search construction


class SearchRole(str, Enum):
    ESSENTIAL = "essential"

    # ADDED:
    # A strong answer-bearing concept that improves precision but is not safe
    # to require in every passage-level query.
    IMPORTANT = "important"

    CONTEXTUAL = "contextual"

    TARGET_ENTITY = "target_entity"

    # ADDED:
    # Identifies the author, work, document, chapter, speaker, collection,
    # or other source in which the answer should be sought.
    SOURCE_REFERENCE = "source_reference"


class SearchTerm(BaseModel):
    text: str = Field(
        min_length=1,
        description=(
            "The user's original word or phrase representing this semantic search "
            "concept. Preserve the wording from the user's question. Do not replace "
            "it with a synonym, normalized label, or inferred related concept."
        ),
    )

    role: SearchRole = Field(
        description=(
            "Classify the concept according to its passage-retrieval function. "
            "'target_entity' identifies the person, organization, place, event, or "
            "other entity that the requested passages are substantively about and "
            "whose name or alias is normally a strong lexical anchor. There should be only one target_entity. "
            "'essential' is an indispensable answer-bearing concept describing what "
            "must be said about the target. "
            "'important' is strongly useful answer-bearing content that improves "
            "precision but need not appear in every relevant passage. "
            "'contextual' provides optional supporting context. "
            "'source_reference' identifies the author, work, document, chapter, "
            "speaker, or collection in which the answer should be sought."
        ),
    )

    is_phrase: bool = Field(
        default=False,
        description=(
            "Set to true when the original text should normally be searched as an "
            "exact multiword expression, such as a person's full or multi-word name, quotation, "
            "fixed technical expression, or multi-word identifier. Do not set this to true "
            "merely because a semantic concept contains more than one word."
        ),
    )

    variants: list[str] = Field(
        default_factory=list,
        max_length=3,
        description=(
            "Zero to three close lexical alternatives for the same semantic concept. "
            "Variants are permitted only when the role is 'essential', 'important', and 'target_entity'. "
            "For 'contextual' and 'source_reference' terms, return an empty list. "
            "Variants may include close synonyms, aliases, abbreviations, alternate "
            "spellings, standard translations, inflectional forms not handled by the "
            "tokenizer, or established domain terminology that could realistically "
            "occur in the corpus. Do not repeat the original text. Do not include "
            "broader categories, narrower examples, associated ideas, causes, effects, "
            "implications, or merely related concepts."
        ),
    )

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = " ".join(value.strip().split())

        if not value:
            raise ValueError("Search term cannot be empty.")

        return value

    @field_validator("variants")
    @classmethod
    def clean_variants(cls, variants: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for variant in variants:
            variant = " ".join(variant.strip().split())

            if not variant:
                continue

            key = variant.casefold()

            if key not in seen:
                cleaned.append(variant)
                seen.add(key)

        return cleaned

    @model_validator(mode="after")
    def validate_term(self) -> "SearchTerm":
        original = self.text.casefold()

        # RETAINED, but generalized:
        # The original wording is searched separately and must not also appear
        # as a variant.
        self.variants = [
            variant for variant in self.variants if variant.casefold() != original
        ]

        # REMOVED:
        # if self.is_phrase and self.variants:
        #     raise ValueError("Phrases must not have lexical variants.")
        #
        # Reason:
        # A phrase may have legitimate alternate forms. For example:
        # "Meditations" -> "The Meditations"
        # "United States" -> "US", "U.S."

        return self


class SearchTerms(BaseModel):
    terms: list[SearchTerm] = Field(
        min_length=1,
        description=(
            "A minimal set of independent semantic concepts extracted from the "
            "user's question for lexical passage retrieval. Each term represents "
            "one concept; its variants represent alternative lexical realizations "
            "of that same concept."
        ),
    )

    @model_validator(mode="after")
    def validate_search_plan(self) -> "SearchTerms":
        role_priority = {
            SearchRole.TARGET_ENTITY: 4,
            SearchRole.ESSENTIAL: 3,
            SearchRole.IMPORTANT: 2,
            SearchRole.CONTEXTUAL: 1,
            SearchRole.SOURCE_REFERENCE: 0,
        }

        terms_by_text: dict[str, SearchTerm] = {}
        term_order: list[str] = []

        for term in self.terms:
            key = term.text.casefold()

            if key not in terms_by_text:
                terms_by_text[key] = term
                term_order.append(key)
                continue

            existing = terms_by_text[key]

            # Preserve the stronger retrieval role.
            if role_priority[term.role] > role_priority[existing.role]:
                existing.role = term.role

            # Preserve phrase behaviour if either occurrence requires it.
            existing.is_phrase = existing.is_phrase or term.is_phrase

            # Merge variants while preserving order and removing duplicates.
            existing_forms = {
                existing.text.casefold(),
                *(variant.casefold() for variant in existing.variants),
            }

            for variant in term.variants:
                variant_key = variant.casefold()

                if variant_key in existing_forms:
                    continue

                existing.variants.append(variant)
                existing_forms.add(variant_key)

                if len(existing.variants) == 3:
                    break

        self.terms = [terms_by_text[key] for key in term_order]

        has_required_concept = any(
            term.role
            in {
                SearchRole.ESSENTIAL,
                SearchRole.TARGET_ENTITY,
            }
            for term in self.terms
        )

        if not has_required_concept:
            raise ValueError(
                "At least one term must be classified as essential or target_entity."
            )

        return self
