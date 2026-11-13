#!/usr/bin/env python3

import click
import locale
import logging
import sys
from pathlib import Path
from typing import Optional
from classeur import Classeur
from document import Document
from logging_config import setup_logging_from_cli
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CliOptions:
    source: Optional[str] = None
    log: str = "warn"
    base: Optional[str] = None
    extracteur: Optional[str] = None
    pages: Optional[int] = None
    ranger: bool = False
    texte: bool = False

def trouver_base_recherche(base: str, source: str) -> Path:
    """Détermine le dossier de base pour la recherche des classeurs.
    
    Args:
        base: Dossier de base fourni en argument (peut être None)
        source: Argument SOURCE (fichier ou dossier)
        
    Returns:
        Chemin absolu du dossier où chercher les classeurs
    """
    if base:
        return Path(base).resolve()
    
    source_path = Path(source).resolve()
    
    if source_path.is_file():
        return source_path.parent
    elif source_path.is_dir():
        return source_path
    else:
        return Path.cwd()


def trouver_fichiers_pdf(source: str) -> list:
    """Trouve tous les fichiers PDF à partir de la source.
    
    Args:
        source: Chemin vers un fichier PDF ou un dossier contenant des PDFs
        
    Returns:
        Liste des chemins des fichiers PDF trouvés
        
    Raises:
        ValueError: Si la source n'est pas valide
    """
    source_path = Path(source).resolve()
    pdf_files = []
    
    if source_path.is_file():
        if source_path.suffix.lower() == '.pdf':
            pdf_files.append(source_path.resolve())
        else:
            raise ValueError(f"Le fichier source n'est pas un PDF: {source_path}")
    elif source_path.is_dir():
        # Chercher tous les fichiers avec extension .pdf (n'importe quelle casse)
        for pdf_file in source_path.glob('*.pdf'):
            if pdf_file.is_file():
                pdf_files.append(pdf_file.resolve())
        
        for pdf_file in source_path.rglob('*.PDF'):
            if pdf_file.is_file():
                resolved = pdf_file.resolve()
                if resolved not in pdf_files:
                    pdf_files.append(resolved)
        
        for pdf_file in source_path.rglob('*.Pdf'):
            if pdf_file.is_file():
                resolved = pdf_file.resolve()
                if resolved not in pdf_files:
                    pdf_files.append(resolved)
        
        if not pdf_files:
            raise ValueError(f"Aucun fichier PDF trouvé dans le dossier: {source_path}")
    else:
        raise ValueError(f"La source n'est ni un fichier ni un dossier: {source_path}")
    
    return pdf_files


def identifier_document(document: Document, classeurs: list) -> Optional[Classeur]:
    """Identifie à quel classeur appartient un document.
    
    Args:
        document: Document à identifier
        classeurs: Liste des classeurs disponibles
        
    Returns:
        Classeur correspondant ou None si aucun ne correspond
    """
    for classeur in classeurs:
        texte = document.extract_text(classeur)
        if texte is None:
            logger.warning(f"aucun texte extrait du document: {document.name}")
            continue

        if classeur.can_identify_document(texte):
            logger.info(f"document {document.name} identifié dans le classeur {classeur}")
            return classeur

    logger.warning(f"document {document.name} non identifié dans aucun classeur")
    print(f"  ❌ Le document {document.name} ne correspond à aucun classeur")
    return None


@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("-l", "--log", type=click.Choice(["info", "warn", "error", "debug", "none"],
        case_sensitive=False), default="none", show_default=True, help="niveau de journalisation")
@click.option("-b", "--base", type=click.Path(), help="dossier de base des classeurs")
@click.option("-e", "--extracteur", type=click.Choice(["mac", "simple", "tolerant"],
        case_sensitive=False), show_default=True, help="choix du module d'extraction")
@click.option("-p", "--pages", type=int, help="nombre de pages à extraire")
@click.option("-r", "--ranger", is_flag=True, help="range le(s) document(s) dans le classeur identifié")
@click.option("-t", "--texte", is_flag=True, help="affiche le texte extrait")
def classement(source: str, log: str, base: str, extracteur: str, pages:int,  ranger: bool, texte: bool):
    """Classement des fichiers à partir de SOURCE"""
    initialise_logging(log)
    cli_options: CliOptions = CliOptions(source, log, base, extracteur, pages, ranger, texte)
    logger.debug(f"options CLI: {cli_options}")
    
    # Traiter l'argument 'base' pour trouver les classeurs
    base_recherche = trouver_base_recherche(base, source)
    classeurs = Classeur.find_classeurs(str(base_recherche))
    
    if not classeurs:
        print("❌ Il n'y a pas de fichier de configuration")
        sys.exit(1)
    
    # Lister les classeurs trouvés
    print(f"Classeurs trouvés dans la base {base_recherche}:")
    for classeur in classeurs:
        print(f"  - {classeur}")
    
    # Conserver la liste des instances Classeur pour une utilisation ultérieure
    logger.debug(f"nombre de classeurs trouvés: {len(classeurs)}")
    
    # Traiter l'argument SOURCE
    try:
        pdf_files = trouver_fichiers_pdf(source)
    except ValueError as e:
        logger.error(f"erreur de validation de la source: {e}")
        print(f"❌ Erreur: {e}")
        sys.exit(1)
    
    # Afficher le nom de chaque fichier PDF
    # print("\nFichiers PDF à traiter:")
    # for pdf_file in pdf_files:
    #     print(f"  - {pdf_file.name}")
    
    logger.debug(f"nombre de fichiers PDF trouvés: {len(pdf_files)}")
    
    # Identification des documents
    print("\nIdentification des documents:")
    for pdf_file in pdf_files:
        print(f"🗂️ Document: {pdf_file.name}...")
        try:
            document = Document.from_path(str(pdf_file))
            document.extracteur = cli_options.extracteur
            document.pages = cli_options.pages
            classeur_trouve = identifier_document(document, classeurs)
            
            if classeur_trouve:
                print(f"  ✅ Classeur: {classeur_trouve.get_description() or 'inconnu'}")
            else:
                print("  ❌ Aucun classeur correspondant")
                continue

            classement_ok = document.classement(classeur_trouve)
            if classement_ok:
                print("  ✅ Document classé correctement (nom de fichier, dossier, timestamp et permissions corrects)")
            else:
                print(f"  ❌ {'✓' if document.nom_fichier_ok else '𐄂'} nom du fichier ({document.nom_fichier})"
                      f" - {'✓' if document.classeur_ok else '𐄂'} bon classeur"
                      f" - {'✓' if document.timestamp_fichier_ok else '𐄂'} timestamp"
                      f" - {'✓' if document.permission_fichier_ok else '𐄂'} permissions")
                if not cli_options.ranger:
                    print("  ℹ️ Utilise l'option '--ranger' pour classer le document")
                if cli_options.ranger and document.ranger(classeur_trouve):
                    print(f"  ✅ Document classé correctement: {document.path.name}")


        except Exception as e:
            logger.error(f"erreur lors du traitement du document {pdf_file.name}: {e}")
            print(f"  ⚠️ Erreur: {e}")


def initialise_logging(log):
    setup_logging_from_cli(
        log,
        module_levels={"classeur": log, "document": log}
    )

# Wrapper pour tracer automatiquement
def trace_calls(frame, event, arg):
    if event == 'call':
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name
        # Ignorez les fichiers internes de Python si besoin
        if 'appl.classeur/src' in filename:
            logger.debug(f"Appel de {func_name} ({filename}:{lineno})")
    return trace_calls

# TRACE: Activer le traceur au début du script (inactiver en mode debug!)
#sys.settrace(trace_calls)

if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, 'fr_CH.UTF-8')
    classement()
