"""Réexécute intégralement le notebook de régression corrigé.

Prérequis : python importation_données.py. Le notebook n'est remplacé qu'après
succès de toutes ses cellules. Les contrôles de rang, valeurs finies et
groupes spatiaux sont intégrés aux cellules d'estimation.
"""
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from importation_données import MOIS, chemin_cache


def main():
    racine = Path(__file__).resolve().parent
    for annee in [2024, 2026]:
        for mois in MOIS:
            if not chemin_cache(annee, mois).is_file():
                raise FileNotFoundError(f"Cache absent : {annee} {mois}. Exécuter python importation_données.py.")
    chemin = racine / "regression_sur_le_prix.ipynb"
    notebook = nbformat.read(chemin, as_version=4)
    for cellule in notebook.cells:
        if cellule.cell_type == "code":
            cellule.outputs = []
            cellule.execution_count = None
    NotebookClient(notebook, timeout=300, kernel_name="python3",
                   resources={"metadata": {"path": str(racine)}}).execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, chemin)
    print("Toutes les cellules de la régression ont été exécutées et enregistrées sans erreur.")


if __name__ == "__main__":
    main()
