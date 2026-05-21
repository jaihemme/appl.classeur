#!/usr/bin/env python3

import click
import locale
import logging
from document import Document


# root logger haut → bibliothèques tierces silencieuses
logging.basicConfig(level=logging.WARNING)

# handler et logger pour ton application
handler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.addHandler(handler)

@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("-l", "--log", type=click.Choice(["info", "warn", "error", "debug", "none"],
        case_sensitive=False), default="INFO", show_default=True, help="Niveau de journalisation.")
@click.option("-b", "--base", type=click.Path(), default=None, help="Dossier de base des classeurs.")
@click.option("-m", "--module", type=click.Choice(["mac", "simple", "tolerant"],
        case_sensitive=False), default=None, show_default=True, help="Choix du module d'extraction")
@click.option("-r", "--ranger", is_flag=True, help="Range le(s) document(s) dans le classeur.")
def classement(source, log, base, module, ranger):
    """Classement des fichiers à partir de SOURCE."""
    initialise_logging(log)
    logger.debug(f"arguments: source:{source} - base:{base} - module:{module} - range:{ranger}")

    document = Document(source, base, module, ranger)

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
    niveau = ({"info": logging.INFO, "warn": logging.WARNING, "error": logging.ERROR,
               "debug": logging.DEBUG, "none": None}
              .get(log, logging.WARNING))
    if niveau:
        handler.setLevel(niveau)
        logger.setLevel(niveau)
        logging.getLogger("classeur").setLevel(niveau)
        logging.getLogger("document").setLevel(niveau)
    else:
        logging.disable()


if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'fr_CH.UTF-8')
    classement()