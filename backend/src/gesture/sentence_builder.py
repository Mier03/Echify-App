# backend/src/gesture/sentence_builder.py
"""
SentenceBuilder — updated for new 33-label FSL dataset.

Labels by category:
  POLITENESS : HELLO, PLEASE, THANKS, SORRY, GOODBYE, MORNING, AFTERNOON
  ACTIONS    : WANT, HELP, GO, EAT, SLEEP, UNDERSTAND, KNOW
  QUESTIONS  : HOW, WHAT, WHERE, WHY, WHO
  PEOPLE     : I, YOU, ME, FRIEND, FAMILY
  ANSWERS    : YES, NO, OKAY, GOOD, BAD
  TIME       : TODAY
  PLACE      : HOME, HERE, FROM
"""

import time
from typing import List, Optional, Tuple


class SentenceBuilder:

    def __init__(self, short_pause: float = 0.8, long_pause: float = 2.2, max_tokens: int = 25):
        self.short_pause   = short_pause
        self.long_pause    = long_pause
        self.max_tokens    = max_tokens

        self.tokens:           List[str]      = []
        self.pause_start_time: Optional[float] = None
        self.last_token_time:  Optional[float] = None

        # ── Category sets (new labels) ────────────────────────────────────────
        self.politeness = {"HELLO", "PLEASE", "THANKS", "SORRY", "GOODBYE", "MORNING", "AFTERNOON"}
        self.actions    = {"WANT", "HELP", "GO", "EAT", "SLEEP", "UNDERSTAND", "KNOW"}
        self.questions  = {"HOW", "WHAT", "WHERE", "WHY", "WHO"}
        self.people     = {"I", "YOU", "ME", "FRIEND", "FAMILY"}
        self.subjects   = {"I", "YOU", "ME"}
        self.answers    = {"YES", "NO", "OKAY", "GOOD", "BAD"}
        self.time_words = {"TODAY"}
        self.places     = {"HOME", "HERE", "FROM"}

        # tokens that should never appear in a sentence
        self.ignore_tokens = {
            "WAITING", "COLLECTING...", "BUFFERING...", "UNKNOWN",
            "WAITING...", "SIGNING...", "TOO SHORT / IGNORED", ""
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Token collection
    # ──────────────────────────────────────────────────────────────────────────
    def add_token(self, token: str) -> Optional[Tuple[str, str]]:
        now   = time.time()
        token = token.strip().upper()

        if token in self.ignore_tokens:
            return None

        # skip immediate consecutive duplicates
        if self.tokens and self.tokens[-1] == token:
            self.last_token_time = now
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

        if (now - self.pause_start_time) >= self.long_pause and self.tokens:
            return self.finalize()

        return None

    def finalize(self) -> Tuple[str, str]:
        raw = " ".join(self.tokens).strip()
        eng = self.expand(raw)
        self.tokens           = []
        self.pause_start_time = None
        self.last_token_time  = None
        return raw, eng

    def reset(self):
        self.tokens           = []
        self.pause_start_time = None
        self.last_token_time  = None

    # ──────────────────────────────────────────────────────────────────────────
    # Canonicalization — fix token order before expansion
    # ──────────────────────────────────────────────────────────────────────────
    def _canonicalize(self, toks: List[str]) -> List[str]:
        toks = self._dedupe_consecutive(toks)

        # PLEASE always comes first
        if "PLEASE" in toks and toks[0] != "PLEASE":
            toks.remove("PLEASE")
            toks.insert(0, "PLEASE")

        # Question word comes first
        for q in self.questions:
            if q in toks and toks[0] != q:
                toks.remove(q)
                toks.insert(0, q)
                break

        # WHERE + subject + GO/HOME → normalize
        if "WHERE" in toks and any(p in toks for p in self.people):
            return ["WHERE"] + [t for t in toks if t != "WHERE"]

        # Subject–Verb–Place (SVO) ordering
        subj  = next((t for t in toks if t in self.subjects), None)
        verb  = next((t for t in toks if t in self.actions),  None)
        place = next((t for t in toks if t in self.places),   None)

        if subj and verb:
            rest = [t for t in toks if t not in {subj, verb}]
            toks = [subj, verb] + rest

        return toks

    # ──────────────────────────────────────────────────────────────────────────
    # Expansion — gloss tokens → natural English
    # ──────────────────────────────────────────────────────────────────────────
    def expand(self, raw: str) -> str:
        toks = [t for t in raw.upper().split() if t]
        if not toks:
            return ""

        toks   = self._canonicalize(toks)
        joined = " ".join(toks)

        # ── Single tokens ─────────────────────────────────────────────────────
        if len(toks) == 1:
            t = toks[0]
            if t == "HELLO":        return "Hello!"
            if t == "GOODBYE":      return "Goodbye!"
            if t == "THANKS":       return "Thank you."
            if t == "SORRY":        return "Sorry."
            if t == "PLEASE":       return "Please."
            if t == "MORNING":      return "Good morning!"
            if t == "AFTERNOON":    return "Good afternoon!"
            if t == "YES":          return "Yes."
            if t == "NO":           return "No."
            if t == "OKAY":         return "Okay."
            if t == "GOOD":         return "Good."
            if t == "BAD":          return "Bad."
            if t == "TODAY":        return "Today."
            if t == "HOME":         return "Home."
            if t == "HERE":         return "Here."
            if t == "FROM":         return "From."
            if t == "HELP":         return "Help!"
            if t == "WANT":         return "Want."
            if t == "GO":           return "Go."
            if t == "EAT":          return "Eat."
            if t == "SLEEP":        return "Sleep."
            if t == "UNDERSTAND":   return "Understand."
            if t == "KNOW":         return "Know."
            if t == "I":            return "I."
            if t == "YOU":          return "You."
            if t == "ME":           return "Me."
            if t == "FRIEND":       return "Friend."
            if t == "FAMILY":       return "Family."
            if t in self.questions: return f"{t.title()}?"
            return f"{t.title()}."

        # ── Greetings ─────────────────────────────────────────────────────────
        if joined == "HELLO PLEASE":        return "Hello, please."
        if joined == "HELLO THANKS":        return "Hello, thank you."
        if joined == "HELLO GOODBYE":       return "Hello and goodbye."
        if joined == "MORNING HELLO":       return "Good morning!"
        if joined == "AFTERNOON HELLO":     return "Good afternoon!"
        if joined == "SORRY PLEASE":        return "Sorry, please."
        if joined == "THANKS PLEASE":       return "Thank you, please."

        # ── Questions ─────────────────────────────────────────────────────────
        if joined == "HOW YOU":             return "How are you?"
        if joined == "HOW I":               return "How am I?"
        if joined == "WHAT YOU WANT":       return "What do you want?"
        if joined == "WHAT YOU EAT":        return "What do you eat?"
        if joined == "WHAT YOU KNOW":       return "What do you know?"
        if joined == "WHERE YOU GO":        return "Where are you going?"
        if joined == "WHERE YOU FROM":      return "Where are you from?"
        if joined == "WHERE HOME":          return "Where is home?"
        if joined == "WHERE YOU":           return "Where are you?"
        if joined == "WHO YOU":             return "Who are you?"
        if joined == "WHO FRIEND":          return "Who is your friend?"
        if joined == "WHO FAMILY":          return "Who is your family?"
        if joined == "WHY YOU GO":          return "Why are you going?"
        if joined == "WHY YOU SLEEP":       return "Why are you sleeping?"
        if joined == "WHY YOU HERE":        return "Why are you here?"

        # ── YES/NO + action ───────────────────────────────────────────────────
        if joined == "YES UNDERSTAND":      return "Yes, I understand."
        if joined == "NO UNDERSTAND":       return "No, I don't understand."
        if joined == "YES KNOW":            return "Yes, I know."
        if joined == "NO KNOW":             return "No, I don't know."
        if joined == "OKAY GOOD":           return "Okay, good."
        if joined == "YES GOOD":            return "Yes, good."
        if joined == "NO BAD":              return "No, bad."

        # ── I/YOU + action (subject–verb) ─────────────────────────────────────
        if len(toks) == 2 and toks[0] in self.subjects and toks[1] in self.actions:
            subj = "I" if toks[0] in {"I", "ME"} else "You"
            verb = toks[1].lower()
            verb_map = {
                "want":       f"{subj} want.",
                "help":       f"{subj} need help." if subj == "I" else f"{subj} need help.",
                "go":         f"{subj} go." if subj == "I" else f"{subj} go.",
                "eat":        f"{subj} eat.",
                "sleep":      f"{subj} sleep.",
                "understand": f"{subj} understand.",
                "know":       f"{subj} know.",
            }
            return verb_map.get(verb, f"{subj} {verb}.")

        # ── I/YOU + GO + PLACE ────────────────────────────────────────────────
        if len(toks) == 3 and toks[0] in self.subjects and toks[1] == "GO" and toks[2] in self.places:
            subj  = "I" if toks[0] in {"I", "ME"} else "You"
            place = toks[2].lower()
            place_map = {"home": "home", "here": "here", "from": "from here"}
            return f"{subj} go {place_map.get(place, place)}."

        # ── I/YOU + WANT + action/place ───────────────────────────────────────
        if len(toks) == 3 and toks[0] in self.subjects and toks[1] == "WANT":
            subj = "I" if toks[0] in {"I", "ME"} else "You"
            obj  = toks[2]
            if obj in self.actions:
                return f"{subj} want to {obj.lower()}."
            if obj in self.places:
                return f"{subj} want to go {obj.lower()}."
            if obj in self.people:
                return f"{subj} want {obj.lower()}."
            return f"{subj} want {obj.title()}."

        # ── I/YOU + GO + HOME (common phrase) ────────────────────────────────
        if toks == ["I", "GO", "HOME"] or toks == ["ME", "GO", "HOME"]:
            return "I'm going home."
        if toks == ["YOU", "GO", "HOME"]:
            return "You're going home."

        # ── PLEASE + action ───────────────────────────────────────────────────
        if len(toks) == 2 and toks[0] == "PLEASE" and toks[1] in self.actions:
            return f"Please {toks[1].lower()}."
        if len(toks) == 2 and toks[0] == "PLEASE" and toks[1] in self.places:
            return f"Please go {toks[1].lower()}."

        # ── HELP + subject ────────────────────────────────────────────────────
        if len(toks) == 2 and toks[0] == "HELP" and toks[1] in self.subjects:
            subj = "me" if toks[1] in {"I", "ME"} else "you"
            return f"Help {subj}!"
        if len(toks) == 2 and toks[0] in self.subjects and toks[1] == "HELP":
            subj = "I" if toks[0] in {"I", "ME"} else "You"
            return f"{subj} need help!"

        # ── TODAY + action ────────────────────────────────────────────────────
        if len(toks) == 2 and toks[0] == "TODAY" and toks[1] in self.actions:
            return f"Today, {toks[1].lower()}."
        if len(toks) >= 2 and toks[0] in self.subjects and toks[1] in self.actions and "TODAY" in toks:
            subj  = "I" if toks[0] in {"I", "ME"} else "You"
            verb  = toks[1].lower()
            return f"{subj} {verb} today."

        # ── FRIEND/FAMILY + action ────────────────────────────────────────────
        if len(toks) == 2 and toks[0] in {"FRIEND", "FAMILY"} and toks[1] in self.actions:
            return f"{toks[0].title()} {toks[1].lower()}s."
        if len(toks) == 2 and toks[0] in self.subjects and toks[1] in {"FRIEND", "FAMILY"}:
            subj = "My" if toks[0] in {"I", "ME"} else "Your"
            return f"{subj} {toks[1].lower()}."

        # ── FROM + PLACE ──────────────────────────────────────────────────────
        if len(toks) == 2 and toks[0] == "FROM" and toks[1] in self.places:
            return f"From {toks[1].lower()}."
        if len(toks) == 2 and toks[0] in self.subjects and toks[1] == "FROM":
            subj = "I" if toks[0] in {"I", "ME"} else "You"
            return f"{subj} am from here." if subj == "I" else f"{subj} are from here."

        # ── Questions with question word ──────────────────────────────────────
        if toks[0] in self.questions:
            rest = " ".join(t.lower() for t in toks[1:])
            return f"{toks[0].title()} {rest}?"

        # ── Default fallback ──────────────────────────────────────────────────
        return " ".join(t.title() for t in toks) + "."

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────
    def _dedupe_consecutive(self, toks: List[str]) -> List[str]:
        out = []
        for t in toks:
            if not out or t != out[-1]:
                out.append(t)
        return out

    def _to_sentence(self, s: str, punct: str = ".") -> str:
        s = s.strip()
        if not s:
            return ""
        if punct and not s.endswith((".", "!", "?", ",")):
            return s + punct
        return s