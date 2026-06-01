from dataclasses import dataclass

@dataclass(frozen=True)
class CliOptions:
    source: str = None
    log: str = "none"
    base: str = None
    extractor: str = "simple"
    ranger: bool = False
    texte: bool = False
