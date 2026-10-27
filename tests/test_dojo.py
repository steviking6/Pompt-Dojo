"""Tests de nettoyer_texte et parser_reponse (aucun appel au LLM)."""
import pytest

from dojo import Sinistre, nettoyer_texte, parser_reponse  # adapte si tes fonctions sont dans un autre module

# Réponse « parfaite » du LLM, réutilisée dans plusieurs tests
JSON_VALIDE = '{"type": "auto", "date": "2026-10-18", "montant": 1850.0, "urgence": "haute"}'


# ---------------------------------------------------------------------------
# nettoyer_texte
# ---------------------------------------------------------------------------

def test_nettoyer_sans_balises_ne_change_rien():
    assert nettoyer_texte(JSON_VALIDE) == JSON_VALIDE


def test_nettoyer_retire_balises_json():
    texte = f"```json\n{JSON_VALIDE}\n```"
    assert nettoyer_texte(texte) == JSON_VALIDE


def test_nettoyer_retire_balises_sans_langage():
    texte = f"```\n{JSON_VALIDE}\n```"
    assert nettoyer_texte(texte) == JSON_VALIDE


def test_nettoyer_ignore_espaces_et_sauts_de_ligne_autour():
    texte = f"\n\n  ```json\n{JSON_VALIDE}\n```  \n"
    assert nettoyer_texte(texte) == JSON_VALIDE


def test_nettoyer_balise_fermante_manquante():
    # Réponse tronquée par le LLM : seule la balise d'ouverture est retirée
    texte = f"```json\n{JSON_VALIDE}"
    assert nettoyer_texte(texte) == JSON_VALIDE


@pytest.mark.parametrize("texte", "", ids=["vide", "espaces"])
def test_nettoyer_texte_vide_ne_plante_pas(texte):
    # Vérifie que les gardes « if lignes » évitent une IndexError
    assert nettoyer_texte(texte) == ""


# ---------------------------------------------------------------------------
# parser_reponse : cas valides
# ---------------------------------------------------------------------------

def test_parser_json_valide_renvoie_sinistre():
    resultat = parser_reponse(JSON_VALIDE)
    assert isinstance(resultat, Sinistre)
    assert resultat.type == "auto"
    assert resultat.date == "2026-10-18"
    assert resultat.montant == 1850.0
    assert resultat.urgence == "haute"


def test_parser_json_entre_balises():
    resultat = parser_reponse(f"```json\n{JSON_VALIDE}\n```")
    assert resultat is not None
    assert resultat.montant == 1850.0


def test_parser_montant_null_accepte():
    # Piège « sans montant » : null est une réponse correcte, pas une erreur
    texte = '{"type": "habitation", "date": "2026-10-20", "montant": null, "urgence": "haute"}'
    resultat = parser_reponse(texte)
    assert resultat is not None
    assert resultat.montant is None


# ---------------------------------------------------------------------------
# parser_reponse : cas invalides → None, jamais d'exception
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "texte",
    [
        "",
        "Il s'agit d'un accident de voiture, urgence haute.",
        '{"type": "auto", "date": "2026-10-18"',
        '{"type": "voiture", "date": "2026-10-18", "montant": 1850.0, "urgence": "haute"}',
        '{"type": "auto", "date": "2026-10-18", "montant": 1850.0, "urgence": "critique"}',
        '{"type": "auto", "date": "2026-10-18", "montant": -50.0, "urgence": "haute"}',
        '{"date": "2026-10-18", "montant": 1850.0, "urgence": "haute"}',
        f"Voici le JSON demandé : {JSON_VALIDE}",
    ],
    ids=[
        "vide",
        "pas_du_json",
        "json_tronque",
        "type_hors_liste",
        "urgence_hors_liste",
        "montant_negatif",
        "type_manquant",
        "texte_avant_json",  # limite connue : nettoyer_texte ne gère que les balises ```
    ],
)
def test_parser_reponse_invalide_renvoie_none(texte):
    assert parser_reponse(texte) is None