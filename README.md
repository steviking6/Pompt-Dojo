# Prompt-Dojo

Évaluation et comparaison mesurée de trois stratégies de prompt engineering (**zero-shot**, **few-shot**, **prompt structuré**) pour l'extraction automatique d'informations de déclarations de sinistre (`auto` / `habitation`) avec un LLM local (`llama3.2` via Ollama) et validation par **Pydantic**.

## Arborescence

```text
Prompt-Dojo/
├── data/
│   ├── GUIDE_ANNOTATION.md  # règles métier appliquées pour annoter le jeu de test
│   ├── jeu_test.json        # 15 emails de déclaration de sinistre annotés
│   └── resultats.csv        # métriques comparées par version de prompt (généré)
├── prompts/
│   ├── v1.txt               # zero-shot (consigne directe)
│   ├── v2.txt               # few-shot (2 exemples hors jeu de test)
│   └── v3.txt               # structuré (règles métier, schéma JSON, délimiteurs <email>)
├── src/
│   └── dojo.py              # modèle Pydantic, nettoyage, parsing et boucle d'évaluation
├── tests/
│   └── test_dojo.py         # tests unitaires pytest (sans appel LLM)
├── pyproject.toml
└── README.md
```

## Exécution

### Lancer les tests unitaires (sans appel LLM)

```bash
pytest -v
```

### Lancer l'évaluation des 3 versions de prompts (Ollama requis)

```bash
python src/dojo.py
```
