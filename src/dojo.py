import csv
import json
from pathlib import Path
from typing import Literal

import ollama
from pydantic import BaseModel, Field, ValidationError

PLACEHOLDERS = ["{email}", "{date_reception}"]

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_PROMPTS = RACINE / "prompts"
DOSSIER_DATA = RACINE / "data"


class Sinistre(BaseModel):
    type: Literal["auto", "habitation"]
    date: str | None = None
    montant: float | None = Field(default=None, gt=0)
    urgence: Literal["basse", "moyenne", "haute"]


def generer(prompt: str, temperature: float, modele: str = "llama3.2") -> str:
    r = ollama.chat(
        model=modele,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    return r["message"]["content"]


def nettoyer_texte(texte: str) -> str:
    lignes = texte.strip().splitlines()

    if lignes and lignes[0].strip().startswith("```"):
        lignes.pop(0)

    if lignes and lignes[-1].strip() == "```":
        lignes.pop(-1)

    return "\n".join(lignes).strip()


def parser_reponse(texte: str) -> Sinistre | None:
    txt = nettoyer_texte(texte)
    if not txt:
        return None
    try:
        return Sinistre.model_validate_json(txt)
    except ValidationError:
        return None


def charger_prompt(version: str, dossier: Path = DOSSIER_PROMPTS) -> str:
    chemin = dossier / f"{version}.txt"
    return chemin.read_text(encoding="utf-8")


def predire(
    template: str,
    email: str,
    date_reception: str,
    temperature: float = 0,
) -> Sinistre | None:
    """Injecte l'email et sa date de réception, appelle le LLM, parse la réponse."""
    manquants = [p for p in PLACEHOLDERS if p not in template]
    if manquants:
        raise ValueError(f"Placeholders absents du prompt : {manquants}")

    prompt = (
        template
        .replace("{email}", email)
        .replace("{date_reception}", date_reception)
    )
    reponse = generer(prompt, temperature)
    return parser_reponse(reponse)


def evaluer(predit: Sinistre | None, attendu: dict) -> dict:
    """Compare un Sinistre prédit au dictionnaire attendu, champ par champ."""
    champs = list(Sinistre.model_fields)
    if predit is None:
        scores_champs = {champ: False for champ in champs}
        return {
            "json_valide": False,
            **scores_champs,
            "tout_correct": False,
        }

    prediction = predit.model_dump()
    scores_champs = {
        champ: prediction[champ] == attendu[champ]
        for champ in champs
    }
    return {
        "json_valide": True,
        **scores_champs,
        "tout_correct": all(scores_champs.values()),
    }


def evaluer_prompt(version: str, jeu_test: list[dict]) -> dict:
    """Évalue une version de prompt sur tout le jeu de test, champ par champ."""
    template = charger_prompt(version)
    champs = list(Sinistre.model_fields)

    nb_cas = len(jeu_test)
    nb_echecs = 0
    nb_champs_corrects = 0
    nb_champs_total = nb_cas * len(champs)
    nb_emails_corrects = 0

    for cas in jeu_test:
        sinistre = predire(template, cas["email"], cas["date_reception"])
        resultat = evaluer(sinistre, cas["attendu"])

        if not resultat["json_valide"]:
            nb_echecs += 1
            continue

        nb_champs_corrects += sum(resultat[champ] for champ in champs)
        if resultat["tout_correct"]:
            nb_emails_corrects += 1

    return {
        "version": version,
        "taux_json_valide": round((nb_cas - nb_echecs) / nb_cas, 3),
        "taux_echec_format": round(nb_echecs / nb_cas, 3),
        "exactitude_champs": round(nb_champs_corrects / nb_champs_total, 3),
        "exactitude_globale": round(nb_emails_corrects / nb_cas, 3),
    }


def exporter_csv(
    lignes: list[dict],
    chemin: Path = DOSSIER_DATA / "resultats.csv",
) -> None:
    if not lignes:
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=lignes[0].keys())
        writer.writeheader()
        writer.writerows(lignes)


if __name__ == "__main__":
    jeu_test = json.loads(
        (DOSSIER_DATA / "jeu_test.json").read_text(encoding="utf-8")
    )
    resultats = []
    for version in ["v1", "v2", "v3"]:
        score = evaluer_prompt(version, jeu_test)
        resultats.append(score)
        print(score)
    exporter_csv(resultats)
