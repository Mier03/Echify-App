import time
import csv
import os
from typing import Dict, List, Optional, Tuple, Set, FrozenSet


class SentenceBuilder:
    def __init__(self, short_pause: float = 0.8, long_pause: float = 2.2, max_tokens: int = 25):
        self.short_pause = short_pause
        self.long_pause = long_pause
        self.max_tokens = max_tokens

        self.tokens: List[str] = []
        self.pause_start_time: Optional[float] = None
        self.last_token_time: Optional[float] = None

        self.question_words = {"HOW", "WHAT", "WHERE", "WHY", "WHO"}
        self.subject_words = {"I", "ME", "YOU"}
        self.verb_words = {
            "WANT", "HELP", "GO", "EAT", "SLEEP",
            "UNDERSTAND", "KNOW", "LIKE", "LOVE", "NEED"
        }

        # These are structural helpers only. The output phrases themselves now come from phrases.csv.
        self.standalone_phrases: Set[str] = set()
        self.phrase_token_sets: Set[FrozenSet[str]] = set()

        self.ignore_tokens = {
            "WAITING", "COLLECTING...", "BUFFERING...", "UNKNOWN",
            "WAITING...", "SIGNING...", "TOO SHORT / IGNORED",
            "", "COLLECTING..."
        }

        self.word_map = {
            "HELLO": "hello",
            "GOODBYE": "goodbye",
            "THANKS": "thank you",
            "SORRY": "sorry",
            "YES": "yes",
            "NO": "no",
            "OKAY": "okay",
            "GOOD": "good",
            "BAD": "bad",
            "I": "I",
            "ME": "me",
            "YOU": "you",
            "WANT": "want",
            "HELP": "help",
            "GO": "go",
            "EAT": "eat",
            "SLEEP": "sleep",
            "UNDERSTAND": "understand",
            "KNOW": "know",
            "LIKE": "like",
            "LOVE": "love",
            "NEED": "need",
            "HOME": "home",
            "FAMILY": "family",
            "FRIEND": "friend",
            "NAME": "name",
            "FOOD": "food",
            "HERE": "here",
            "FROM": "from",
            "TODAY": "today",
            "WHAT": "what",
            "WHERE": "where",
            "WHY": "why",
            "WHO": "who",
            "HOW": "how",
            "PLEASE": "please",
            "GOOD MORNING": "good morning",
            "GOOD AFTERNOON": "good afternoon",
        }

        self.csv_phrases: Dict[FrozenSet[str], str] = {}
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phrases.csv")
        self._load_csv_phrases(csv_path)

    def _load_csv_phrases(self, csv_path: str) -> None:
        """Read phrases.csv.

        Expected columns: category, token_set, output
        token_set uses | as delimiter, for example: I|WANT|EAT
        Lines starting with # are skipped.
        """
        if not os.path.exists(csv_path):
            return

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().startswith("#"):
                    continue
                if len(row) < 3:
                    continue

                category = row[0].strip().lower()
                token_str = row[1].strip().strip('"').strip("'")
                output = row[2].strip().strip('"').strip("'")

                if token_str.lower() == "token_set":
                    continue

                tokens = frozenset(t.strip().upper() for t in token_str.split("|") if t.strip())
                if not tokens or not output:
                    continue

                self.csv_phrases[tokens] = output
                self.phrase_token_sets.add(tokens)

                if category == "standalone" or len(tokens) == 1:
                    self.standalone_phrases.update(tokens)

    def add_token(self, token: str) -> Optional[Tuple[str, str]]:
        now = time.time()
        token = token.strip().upper()

        if token in self.ignore_tokens:
            return None

        self.tokens.append(token)
        self.last_token_time = now

        if len(self.tokens) >= self.max_tokens:
            return self.finalize()

        return None

    def update_pause(self, hands_detected: bool) -> Optional[Tuple[str, str]]:
        now = time.time()

        if hands_detected:
            self.pause_start_time = None
            return None

        if self.pause_start_time is None:
            self.pause_start_time = now
            return None

        if now - self.pause_start_time >= self.long_pause and self.tokens:
            return self.finalize()

        return None

    def finalize(self) -> Tuple[str, str]:
        raw = " ".join(self.tokens).strip()
        eng = self.expand(raw)

        self.tokens = []
        self.pause_start_time = None
        self.last_token_time = None

        return raw, eng

    def reset(self):
        self.tokens = []
        self.pause_start_time = None
        self.last_token_time = None

    def expand(self, raw: str) -> str:
        toks = [t for t in raw.upper().split() if t]
        if not toks:
            return ""

        toks = self._merge_phrases(toks)
        chunks = self._split_into_chunks(toks)

        rendered = []
        for i, chunk in enumerate(chunks):
            out = self._render_single_chunk(chunk, is_last=(i == len(chunks) - 1))
            if out:
                rendered.append(out)

        return " ".join(rendered) if rendered else self._literal_render(toks)

    def _merge_phrases(self, toks: List[str]) -> List[str]:
        merged = []
        i = 0

        while i < len(toks):
            two_word = f"{toks[i]} {toks[i + 1]}" if i + 1 < len(toks) else None
            if two_word and frozenset([two_word]) in self.csv_phrases:
                merged.append(two_word)
                i += 2
            else:
                merged.append(toks[i])
                i += 1

        return merged

    def _split_into_chunks(self, toks: List[str]) -> List[List[str]]:
        if not toks:
            return []

        chunks: List[List[str]] = []
        current: List[str] = []

        for tok in toks:
            if not current:
                current.append(tok)
                continue

            if self._should_start_new_chunk(current, tok):
                chunks.append(current)
                current = [tok]
            else:
                current.append(tok)

        if current:
            chunks.append(current)

        return self._postprocess_chunks(chunks)

    def _should_start_new_chunk(self, current: List[str], tok: str) -> bool:
        starters = {"PLEASE"} | self.question_words | self.standalone_phrases

        if tok in starters and self._chunk_has_meaning(current):
            return True

        return False

    def _chunk_has_meaning(self, chunk: List[str]) -> bool:
        if not chunk:
            return False

        token_set = frozenset(chunk)

        if token_set in self.csv_phrases:
            return True

        if len(chunk) == 1 and chunk[0] in self.standalone_phrases:
            return True

        if chunk[0] in self.question_words and len(chunk) >= 2:
            return True

        return len(chunk) >= 3

    def _postprocess_chunks(self, chunks: List[List[str]]) -> List[List[str]]:
        if not chunks:
            return []

        merged: List[List[str]] = []

        for chunk in chunks:
            if not merged:
                merged.append(chunk)
                continue

            if self._is_weak_chunk(chunk):
                merged[-1].extend(chunk)
            else:
                merged.append(chunk)

        return merged

    def _is_weak_chunk(self, chunk: List[str]) -> bool:
        return (
            bool(chunk)
            and len(chunk) == 1
            and chunk[0] not in self.standalone_phrases
            and chunk[0] not in self.question_words
        )

    def _render_single_chunk(self, chunk: List[str], is_last: bool = False) -> str:
        exact = self._render_exact(chunk)
        if exact:
            return exact

        fuzzy = self._render_fuzzy(chunk)
        if fuzzy:
            return fuzzy

        return self._grammar_fallback_strict(chunk, is_last=is_last)

    def _render_exact(self, chunk: List[str]) -> Optional[str]:
        frozen = frozenset(chunk)
        if frozen in self.csv_phrases:
            return self.csv_phrases[frozen]

        # Generic repeated phrase support. Example: HELLO HELLO -> Hello! Hello!
        if chunk and all(tok == chunk[0] for tok in chunk):
            single = frozenset([chunk[0]])
            if single in self.csv_phrases:
                return " ".join([self.csv_phrases[single]] * len(chunk))

        return None

    def _render_fuzzy(self, chunk: List[str]) -> Optional[str]:
        token_set = set(chunk)
        best_output = None
        best_score = 0.0

        for expected_tokens, output in self.csv_phrases.items():
            score = self._grammar_similarity_score(token_set, set(expected_tokens), output)
            if score > best_score:
                best_score = score
                best_output = output

        return best_output if best_score >= 0.72 else None

    def _grammar_similarity_score(self, chunk_set: Set[str], expected_set: Set[str], output: str) -> float:
        intersection = len(chunk_set & expected_set)
        union = len(chunk_set | expected_set)
        jaccard = intersection / union if union else 0.0
        size_penalty = abs(len(chunk_set) - len(expected_set)) * 0.08
        score = jaccard - size_penalty

        if "YES" in chunk_set and output.startswith("Yes"):
            score += 0.10
        if "PLEASE" in chunk_set and "please" in output.lower():
            score += 0.10
        if "LOVE" in chunk_set and "love" in output.lower():
            score += 0.08
        if "WANT" in chunk_set and "want" in output.lower():
            score += 0.08
        if "ME" in chunk_set and "my" in output.lower():
            score += 0.08

        return score

    def _grammar_fallback_strict(self, chunk: List[str], is_last: bool = False) -> str:
        if not chunk:
            return ""

        if chunk[0] in self.question_words:
            transformed = self._reorder_without_adding_dataset_words(chunk)
            text = " ".join(transformed).capitalize()
            return text + "?"

        yes_prefix = "YES" in chunk
        please_prefix = "PLEASE" in chunk

        working = [tok for tok in chunk if tok not in {"YES", "PLEASE"}]
        transformed = self._reorder_without_adding_dataset_words(working)

        text = " ".join(transformed).strip()
        if text:
            text = text[0].upper() + text[1:]

        if yes_prefix:
            text = f"Yes. {text}" if text else "Yes."
        if please_prefix:
            text = f"Please {text[0].lower() + text[1:]}" if text else "Please."

        if chunk[-1] == "OKAY":
            core = text.replace(" okay", "").replace(" Okay", "").strip()
            if core and not core.endswith((".", "!", "?")):
                core += "."
            return f"{core} Okay?"

        if not text.endswith((".", "!", "?")):
            text += "."

        return text

    def _reorder_without_adding_dataset_words(self, chunk: List[str]) -> List[str]:
        if not chunk:
            return []

        subject = None
        verb = None
        remainder = []

        for tok in chunk:
            if subject is None and tok in self.subject_words:
                subject = self.word_map.get(tok, tok.lower())
            elif verb is None and tok in self.verb_words:
                verb = self.word_map.get(tok, tok.lower())
            else:
                remainder.append(self.word_map.get(tok, tok.lower()))

        if subject and verb:
            base = [subject, verb] + remainder
        elif verb and remainder:
            base = [verb] + remainder
        else:
            base = [self.word_map.get(tok, tok.lower()) for tok in chunk]

        converted = []
        for i, word in enumerate(base):
            if word == "me" and i + 1 < len(base):
                next_word = base[i + 1]
                if next_word in {"name", "family", "friend", "home", "food"}:
                    word = "my"
            converted.append(word)

        return converted

    def _literal_render(self, chunk: List[str], force_question: bool = False) -> str:
        words = [self.word_map.get(tok, tok.lower()) for tok in chunk]
        text = " ".join(words).capitalize()
        return text + ("?" if force_question else ".")
