"""Pinned, offline-only MiniLM and the game's exact scoring rule."""

import hashlib
import json
import math
import os
import unicodedata
from pathlib import Path

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSIONS = 384


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def points(original: str, guesses: list[str], vectors) -> list[int]:
    if len(vectors) != 3 or len(guesses) != 2:
        raise ValueError("Incomplete scoring batch")
    clean = []
    for vector in vectors:
        if len(vector) != DIMENSIONS:
            raise ValueError("Wrong vector dimensions")
        values = [float(x) for x in vector]
        norm = math.sqrt(sum(x * x for x in values))
        if not all(math.isfinite(x) for x in values) or not math.isfinite(norm) or norm <= 0:
            raise ValueError("Invalid scoring vector")
        clean.append([x / norm for x in values])
    result = []
    for guess, vector in zip(guesses, clean[1:], strict=True):
        cosine = sum(a * b for a, b in zip(clean[0], vector, strict=True))
        result.append(100 if guess == original else math.floor(100 * max(0, min(1, cosine)) + 0.5))
    return result


class LocalScorer:
    ready = False
    token_limit = 256

    def load(self, path: Path) -> None:
        # No fallback to a model name or remote load, including during warm-up.
        manifest = json.loads((path / "vibeparty-model.json").read_text())
        if manifest["model"] != MODEL_ID or manifest["revision"] != MODEL_REVISION:
            raise ValueError("Incorrect model revision")
        required = {
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.txt",
            "config.json",
            "modules.json",
            "sentence_bert_config.json",
            "1_Pooling/config.json",
        }
        if not required <= manifest["sha256"].keys():
            raise ValueError("Incomplete pinned model")
        for name, digest in manifest["sha256"].items():
            candidate = (path / name).resolve()
            if not candidate.is_relative_to(path.resolve()):
                raise ValueError("Invalid model manifest")
            if hashlib.sha256(candidate.read_bytes()).hexdigest() != digest:
                raise ValueError("Model file checksum mismatch")
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            str(path), device="cpu", local_files_only=True, trust_remote_code=False
        )
        self.model.eval()
        self.token_limit = self.model.max_seq_length
        if self.token_limit != 256 or self.model.get_embedding_dimension() != DIMENSIONS:
            raise ValueError("Unexpected model configuration")
        if self.score("A red balloon.", ["A red balloon.", "A blue tower."])[0] != 100:
            raise ValueError("Scorer warm-up failed")
        self.ready = True

    def validate(self, text: str) -> str:
        text = normalize(text)
        if not 1 <= len(text) <= 300:
            raise ValueError("Use 1–300 characters after trimming spaces.")
        if not self.ready:
            raise ValueError("The local scoring model is unavailable. Ask the host to check setup.")
        tokens = self.model.tokenizer(
            text, truncation=False, add_special_tokens=True, verbose=False
        )["input_ids"]
        if len(tokens) > self.token_limit:
            raise ValueError(
                f"Use fewer words or symbols: {len(tokens)} tokens exceeds {self.token_limit}."
            )
        return text

    def score(self, original: str, guesses: list[str]) -> list[int]:
        batch = self.model.encode(
            [original, *guesses],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return points(original, guesses, batch)
