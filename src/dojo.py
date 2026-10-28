from pydantic import BaseModel, Field, ValidationError
from pathlib import Path 
from typing import Literal

import re
import json

from importlib import import_module


class Sinistre(BaseModel):
    type : Literal["auto", "habitation"]
    date : str | None = None 
    montant : float | None =  Field(default=None, gt=0)   
    urgence : Literal["basse", "moyenne", "haute"]

def generer(prompt:str, temperature:float, modele:str = "llama3.2")->str:    
    try:
        ollama = import_module("ollama")
    except ModuleNotFoundError as exc:
        if exc.name == "ollama":
            raise RuntimeError("Install the Ollama Python package with 'pip install ollama'.") from exc
        raise

    r = ollama.chat(model=modele,
                    messages = [{"role":"user", "content":prompt}],
                    options={"temperature":temperature})
    texte = r["message"]["content"]
    return texte 

def nettoyer_texte(texte:str)->str:
    
    match = re.search(r"\{.*\}", texte, re.DOTALL)
    if match is None:
        return None 
    
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None 


def parser_reponse(texte:str)->Sinistre | None: 
    txt = nettoyer_texte(texte)
    try:
       return Sinistre.model_validate_json(txt)
    except ValidationError:
        return None 

def charger_prompt(version : str, dossier:Path = Path("prompts"))->str:
    chemin = dossier / f"{version}.txt"
    return chemin.read_text(encoding="utf-8")  

def prediction(temperature=0, dossier=prompts)->str:...
