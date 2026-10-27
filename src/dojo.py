from pydantic import BaseModel, Field, ValidationError
from pathlib import Path 
from typing import Literal

from importlib import import_module 

class Sinistre(BaseModel):
    type : Literal["auto", "habitation"]
    date : str | None = None 
    montant : float | None =  Field(default=None, gt=0)   
    urgence : Literal["basse", "moyenne", "haute"]

def generer(prompt:str, temperature:float, modele:str)->str:    
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
    lignes = texte.splitlines()
    
    if lignes and lignes[0].strip().startswith("```"):
        lignes.pop(0)
    
    if lignes and lignes[-1].strip() == "```":
        lignes.pop(-1)
    
    return "\n".join(lignes)
        

def parser_reponse(texte:str)->Sinistre | None: 
    txt = nettoyer_texte(texte)
    try:
       return Sinistre.model_validate_json(txt)
    except ValidationError:
        return None 
    
    