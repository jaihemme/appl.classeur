#!/usr/bin/env python3

import click
import locale
import logging
import sys
from dataclasses import dataclass
from document import Document
from logging_config import setup_logging_from_cli

@dataclass(frozen=True)
class CliConfig:
    source: str = None
    log: str = "none"
    base: str = None
    extractor: str = "simple"
    ranger: bool = False
    texte: bool = False


logger = logging.getLogger(__name__)

@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("-l", "--log", type=click.Choice(["info", "warn", "error", "debug", "none"],
        case_sensitive=False), default="none", show_default=True, help="Niveau de journalisation.")
@click.option("-b", "--base", type=click.Path(), help="Dossier de base des classeurs.")
@click.option("-m", "--module", type=click.Choice(["mac", "simple", "tolerant"],
        case_sensitive=False), show_default=True, help="Choix du module d'extraction")
@click.option("-r", "--ranger", is_flag=True, help="Range le(s) document(s) dans le classeur.")
@click.option("-t", "--texte", is_flag=True, help="Affiche le texte extrait.")
def classement(source, log, base, module, ranger, texte):
    """Classement des fichiers à partir de SOURCE."""
    initialise_logging(log)
    cli_config = CliConfig(source, log, base, module, ranger, texte)
    logger.debug(cli_config)
    document = Document(source, base, module, ranger, texte)

    # on a soit un document…
    if isinstance(document, Document):
        print(f"document '{document.chemin.name}' traité")
    # ... soit une liste de fichiers
    if isinstance(document, list):
        if len(document) == 0:
            print("Il n'y a pas de documents dans ce dossier.")
        ok = nok = rok = 0
        for fichier in document:
            d = Document(fichier, base, module, ranger)
            if d.classement_ok:
                ok += 1
            else:
                nok += 1
                if d.identification_ok and d.patterns_ok:
                    rok += 1
        if ok == len(document):
            print(f"\nTous les documents {len(document)} sont corrects")
        else:
            print(f"{nok}/{len(document)} documents sont incorrects")
            print(f"{rok}/{len(document)} documents sont à ranger")


def initialise_logging(log):
    setup_logging_from_cli(
        log,
        module_levels={"classeur": log, "document": log}
    )

if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'fr_CH.UTF-8')
    classement()