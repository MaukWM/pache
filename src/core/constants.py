"""Application constants."""

from enum import Enum


class ItemType(str, Enum):
    """Item type enumeration for SRS system."""

    KANJI = "kanji"
    VOCAB = "vocab"
