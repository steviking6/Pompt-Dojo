import csv
import json
import ollama
import openai
import os

from pathlib import Path
from typing import Callable, Literal

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

openai.api_key = os.getenv('OPENAI_API_KEY')

client = openai.OpenAI()



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


def generer_llama(prompt: str, temperature: float, modele: str = "llama3.2") -> str:
    r = ollama.chat(
        model=modele,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    return r["message"]["content"]

def generer_gpt(prompt: str, temp: float = 1, modele: str = os.getenv('MODEL_NAME')):
    messages = [{"role":"user", "content":prompt}]
    reponse = client.chat.completions.create(
        model=modele,
        reasoning_effort= "low",
        messages=messages,
        temperature=1
    )
    return reponse.choices[0].message.content


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
    generer: Callable = generer_llama,
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


def evaluer_prompt(
    version: str,
    jeu_test: list[dict],
    generer: Callable = generer_llama,
) -> dict:
    """Évalue une version de prompt sur tout le jeu de test, champ par champ."""
    template = charger_prompt(version)
    champs = list(Sinistre.model_fields)

    nb_cas = len(jeu_test)
    nb_echecs = 0
    nb_champs_corrects = 0
    nb_champs_total = nb_cas * len(champs)
    nb_emails_corrects = 0

    for cas in jeu_test:
        sinistre = predire(
            template,
            cas["email"],
            cas["date_reception"],
            generer=generer,
        )
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


def comparer_resultats_csv(
    chemin_llama: Path = DOSSIER_DATA / "resultats_llama.csv",
    chemin_gpt: Path = DOSSIER_DATA / "resultats_gpt.csv",
    chemin_sortie: Path = DOSSIER_DATA / "comparaison.csv",
) -> list[dict]:
    """Compare les fichiers CSV des deux modèles et génère un CSV d'écarts."""
    with open(chemin_llama, "r", encoding="utf-8") as f_llama:
        lignes_llama = {row["version"]: row for row in csv.DictReader(f_llama)}

    with open(chemin_gpt, "r", encoding="utf-8") as f_gpt:
        lignes_gpt = {row["version"]: row for row in csv.DictReader(f_gpt)}

    metriques = [
        "taux_json_valide",
        "taux_echec_format",
        "exactitude_champs",
        "exactitude_globale",
    ]

    comparaison = []
    for version, res_llama in lignes_llama.items():
        if version not in lignes_gpt:
            continue
        res_gpt = lignes_gpt[version]

        ligne_comp = {"version": version}
        for m in metriques:
            val_llama = float(res_llama[m])
            val_gpt = float(res_gpt[m])
            ecart = round(val_gpt - val_llama, 3)

            ligne_comp[f"{m}_llama"] = val_llama
            ligne_comp[f"{m}_gpt"] = val_gpt
            ligne_comp[f"ecart_{m} (gpt-llama)"] = ecart

        # Déterminer le meilleur modèle sur l'exactitude globale
        glob_llama = float(res_llama["exactitude_globale"])
        glob_gpt = float(res_gpt["exactitude_globale"])
        if glob_gpt > glob_llama:
            ligne_comp["meilleur_modele"] = f"gpt (+{round((glob_gpt - glob_llama) * 100, 1)}%)"
        elif glob_llama > glob_gpt:
            ligne_comp["meilleur_modele"] = f"llama (+{round((glob_llama - glob_gpt) * 100, 1)}%)"
        else:
            ligne_comp["meilleur_modele"] = "egalite"

        comparaison.append(ligne_comp)

    exporter_csv(comparaison, chemin_sortie)
    return comparaison


if __name__ == "__main__":
    jeu_test = json.loads(
        (DOSSIER_DATA / "jeu_test.json").read_text(encoding="utf-8")
    )

    modeles = {
        #"llama": generer_llama,
        "gpt": generer_gpt,
    }

    for nom_modele, fonction_generer in modeles.items():
        print(f"--- Évaluation du modèle : {nom_modele} ---")
        resultats = []
        for version in ["v1", "v2", "v3"]:
            score = evaluer_prompt(version, jeu_test, generer=fonction_generer)
            resultats.append(score)
            print(score)
        exporter_csv(resultats, DOSSIER_DATA / f"resultats_{nom_modele}.csv")

    print("--- Comparaison des modèles ---")
    resultats_comparaison = comparer_resultats_csv()
    for ligne in resultats_comparaison:
        print(
            f"Version {ligne['version']} -> Meilleur : {ligne['meilleur_modele']} "
            f"(Exactitude globale : GPT={ligne['exactitude_globale_gpt']} vs Llama={ligne['exactitude_globale_llama']})"
        )
