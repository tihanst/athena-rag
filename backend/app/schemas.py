from typing import Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import NamedTuple


class LLMModel(BaseModel):
    model_provider: str
    model_name: str
    model_endpoint: str
    is_local: bool = False


class ChatHistoryItem(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatSystem(ChatHistoryItem):
    role: Literal["system"] = "system"


class ChatRequest(ChatHistoryItem):
    role: Literal["user"] = "user"
    # message: str
    # history: list[ChatHistoryItem] = []

    # def create_messages_list(self):
    #     hist = [{"role": x.role, "content": x.content} for x in self.history]
    #     hist.append({"role": self.role, "content": self.message})
    #     return hist


class ChatResponse(ChatHistoryItem):
    role: Literal["assistant"] = "assistant"
    # content: str


class FileRecord(BaseModel):
    id: str
    name: str
    size: int
    status: Literal["uploading", "ready", "error"] = "ready"
    description: str | None = None
    document_id: str | None = None


class ContextLoadChunk(NamedTuple):
    document_id: str
    start_db_entry_id: int
    end_db_entry_id: int
    start_char: int
    end_char: int
    content: str


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
            "The user's original word or phrase representing this lexical retrieval "
            "concept. Preserve the wording from the user's question. Include the "
            "concept only when its wording or a close lexical realization is "
            "reasonably likely to provide useful evidence in a relevant passage. "
            "Do not replace it with a synonym, normalized label, or inferred related concept."
        ),
    )

    role: SearchRole = Field(
        description=(
            "Classify the concept according to its lexical passage-retrieval function. "
            "'target_entity' identifies the person, organization, place, event, object, "
            "or other entity that the requested passages are substantively about and "
            "whose name or alias normally provides a strong lexical anchor. There "
            "should normally be only one target_entity. "
            "'essential' is a central and discriminating lexical concept whose wording "
            "or a close lexical equivalent is reasonably likely to occur in an "
            "answer-bearing passage and whose omission would substantially weaken "
            "lexical retrieval. A concept is not essential merely because it is "
            "semantically indispensable to answering the question. "
            "'important' is a useful secondary lexical concept likely to occur in some "
            "relevant passages and capable of improving precision or providing an "
            "additional retrieval route, but which need not occur in every relevant passage. "
            "'contextual' preserves optional thematic, descriptive, situational, or "
            "relational context that may not itself be suitable as a lexical constraint. "
            "'source_reference' identifies the author, work, document, chapter, speaker, "
            "or collection in which the answer should be sought."
        ),
    )

    is_phrase: bool = Field(
        description=(
            "Set to true when the original text should normally be searched as an "
            "exact multiword expression because adjacency and order are important, "
            "such as a person's full or multi-word name, quotation, title, fixed "
            "technical expression, institution, or identifier. Do not set this to "
            "true merely because a concept contains multiple words. This field "
            "describes phrase adjacency only; it does not determine whether the "
            "individual words of a non-phrase term should later be combined with "
            "AND or OR by the lexical query renderer."
        ),
    )

    variants: list[str] = Field(
        default_factory=list,
        min_length=2,
        max_length=4,
        description=(
            "Two to four plausible alternative lexical surface forms of this same "
            "concept. Variants are permitted only for 'essential', 'important', and "
            "'target_entity'. For 'contextual' and 'source_reference', return an "
            "empty list. Generate a variant only when it could realistically occur "
            "in the searchable corpus and improve lexical recall. Zero variants is "
            "preferable to weak, speculative, merely semantic, or unlikely variants. "
            "Variants may include close lexical synonyms, aliases, abbreviations, "
            "alternate spellings, standard translations, inflectional forms not "
            "handled by the tokenizer, or established domain terminology. Do not "
            "repeat the original text. Do not generate ordinary semantic paraphrases, "
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
