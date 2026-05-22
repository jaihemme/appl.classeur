#!/usr/bin/env python3

import click
import locale
from pathlib import Path
from document import Document

@click.command()
@click.argument("fichier_pdf", type=click.Path(exists=True))
@click.option("-p", "--pages", type=int, default=1, help="Nombre de pages.")
@click.option("-m", "--module", type=click.Choice(["mac", "simple", "tolerant"],
        case_sensitive=False), default="mac", show_default=True, help="Divers algorithmes")
def extraire_texte(fichier_pdf, pages, module):
    chemin: Path = Path(fichier_pdf)  # le fichier existe, vérifié par click
    print(f"Fichier: {chemin.resolve()}")
    document = Document(fichier_pdf, None, module, False, True)
    print(f"Document: {document.chemin.name}")
    print(f"Texte extrait avec le module '{document.option_module}' ({document.pages} pages):"
          f"\n{document.extraire_texte()}")


if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'fr_CH.UTF-8')
    extraire_texte()
