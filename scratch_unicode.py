import os
import unicodedata

base = 'impôt'

# Création du nom en NFC (Forme composée)
nom_nfc = unicodedata.normalize('NFC', 'nfd_' + base) # Note: le préfixe n'est pas normalisé différemment ici, c'est le 'ô' qui compte
# En réalité, pour être pur, on normalise tout le string
nom_nfc = unicodedata.normalize('NFC', 'nfc_impôt.pdf')
nom_nfd = unicodedata.normalize('NFD', 'nfd_impôt.pdf')

# Création des fichiers vides
open(nom_nfc, 'w').close()
open(nom_nfd, 'w').close()

print(f'Fichier NFC créé : {repr(nom_nfc)} ({len(nom_nfc)} octets de nom)')
print(f'Fichier NFD créé : {repr(nom_nfd)} ({len(nom_nfd)} octets de nom)')
