# Prompt-Dojo — Tri automatique de déclarations de sinistre

Évaluation et comparaison mesurée de trois stratégies de **prompt engineering** (**zero-shot**, **few-shot**, **prompt structuré**) pour extraire automatiquement les informations clés d'emails de déclaration de sinistre (`auto` / `habitation`) avec un LLM local (`llama3.2` via Ollama) et validation stricte par **Pydantic**.

---

## 1. Problème métier

Dans une compagnie d'assurance, les déclarations de sinistre arrivent par email sous des formes très hétérogènes : courriers formels, messages pressés, SMS bourrés de fautes d'orthographe, textes longs et émotionnels, ou encore déclarations multiples dans un même message.

Pour orienter automatiquement un dossier (ouverture de sinistre, missionnement d'un expert ou d'un dépanneur en urgence, provisionnement financier), il faut extraire de manière fiable **4 champs structurés** :
- `type` : contrat concerné (`"auto"` ou `"habitation"`)
- `date` : date exacte de **survenance** du sinistre (`"AAAA-MM-JJ"` ou `null`)
- `montant` : somme chiffrée des dommages en euros (`float` > 0 ou `null`)
- `urgence` : niveau de priorité opérationnelle (`"basse"`, `"moyenne"` ou `"haute"`)

**Objectif du projet** : mesurer rigoureusement, chiffres à l'appui sur un jeu de test annoté, jusqu'où le *prompt engineering* permet d'emmener un petit modèle local de 3 milliards de paramètres (`llama3.2` à `temperature=0`), et établir un verdict objectif sur son utilisabilité en assurance.

---

## 2. Arborescence du projet

```text
Prompt-Dojo/
├── data/
│   ├── GUIDE_ANNOTATION.md  # règles métier de référence pour l'annotation
│   ├── jeu_test.json        # 15 emails de sinistre annotés avec cas pièges
│   └── resultats.csv        # scores mesurés par version de prompt
├── prompts/
│   ├── v1.txt               # zero-shot (consigne courte + clés attendues)
│   ├── v2.txt               # few-shot (2 exemples hors jeu de test)
│   └── v3.txt               # structuré (règles métier, schéma JSON, délimiteurs <email>)
├── src/
│   └── dojo.py              # modèle Pydantic, nettoyage, parsing et évaluation
├── tests/
│   └── test_dojo.py         # tests unitaires pytest (sans appel au LLM)
├── pyproject.toml
└── README.md
```

---

## 3. Jeu de test et pièges métier (`data/jeu_test.json`)

Le jeu d'évaluation comporte **15 emails fictifs** (soit **60 champs** au total à prédire), construits selon les règles strictes du [Guide d'annotation](file:///mnt/c/Users/stevi/Desktop/IA%20Engineer/Projets_python/Pompt-Dojo/data/GUIDE_ANNOTATION.md) et intégrant les pièges classiques du métier :

- **Dates relatives et distractrices** (`date_relative`, `date_distractrice`, `date_sans_annee`, `format_date_jj_mm`) : résolution de *« hier soir »*, *« ce matin »*, *« samedi dernier »* ou *« mardi »* à partir de `date_reception`, en ignorant la date du devis ou du passage de l'artisan.
- **Pièges sur les montants** (`sans_montant`, `montant_decimal`, `montant_a_additionner`, `montant_franchise`) :
  - Aucun montant chiffré dans les urgences immédiates → `null` attendu (et non `0`).
  - Plusieurs postes de dommages à additionner (ex. `3 150 €` de tuiles + `420 €` de charpente = `3570.0`).
  - Franchise mentionnée dans l'email (ex. `150 €`) à **ne surtout pas** confondre avec le montant des dommages ni soustraire.
- **Ton vs Urgence réelle** (`ton_vs_urgence`, `montant_eleve_vs_urgence`) : un assuré très énervé (`"C'est la DEUXIÈME fois cette année !!!"`, `2 300 €` de grêle esthétique sur une voiture qui roule) relève d'une urgence `basse`, tandis qu'un SMS calme signalant de la fumée sous le capot relève d'une urgence `haute`.
- **Double sinistre** (`double_sinistre`) : deux sinistres dans le même email (rayure auto à `380 €` d'urgence `basse` + fuite active sous évier sans devis d'urgence `haute`) → seul le sinistre **le plus urgent** doit être retenu.

---

## 4. Protocole et versions de prompts

- **Modèle** : `llama3.2` (3B paramètres) en local via Ollama, appelé à **`temperature = 0`** pour garantir la reproductibilité.
- **Validation** : nettoyage des éventuelles balises Markdown ```` ```json ```` via `nettoyer_texte()`, puis validation stricte du schéma et des types via `Sinistre.model_validate_json()` (Pydantic).
- **Les 3 versions testées** :
  1. **`v1` — Zero-shot** : consigne directe demandant un objet JSON avec les 4 clés et leurs types/valeurs autorisés, sans exemple ni explication des règles métier.
  2. **`v2` — Few-shot** : consigne accompagnée de 2 exemples complets (`Date de réception`, `Mail`, `Résultat : {...}`) hors jeu de test, illustrant un cas `"auto"` avec montant et un cas `"habitation"` avec `null`.
  3. **`v3` — Prompt structuré** : définition du rôle métier, règles d'extraction explicites point par point (dates relatives, somme des montants hors franchise, critères objectifs d'urgence, priorité au sinistre le plus urgent), délimiteurs `<email>...</email>`, consigne de sécurité anti-*prompt injection*, et obligation de répondre sur une seule ligne JSON brute.

---

## 5. Résultats mesurés (`data/resultats.csv`)

| Version | Stratégie | JSON valide (%) | Échec de format (%) | Exactitude par champ (%) | Exactitude globale / email (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`v1`** | Zero-shot | 86,7 % *(13/15)* | 13,3 % *(2/15)* | 60,0 % *(36/60)* | 13,3 % *(2/15)* |
| **`v2`** | Few-shot | 0,0 % *(0/15)* | 100,0 % *(15/15)* | 0,0 % *(0/60)* | 0,0 % *(0/15)* |
| **`v3`** | Structuré | **93,3 %** *(14/15)* | **6,7 %** *(1/15)* | **70,0 %** *(42/60)* | **40,0 %** *(6/15)* |

---

## 6. Analyse des erreurs

### Pourquoi `v1` (Zero-shot) plafonne à 13,3 % d'emails parfaits ?
En zero-shot, `llama3.2` respecte globalement le format JSON (13/15 valides) et identifie bien le `type` de contrat (`auto` vs `habitation`), ce qui lui assure 60,0 % de champs corrects. En revanche, dès qu'un seul champ sur les 4 est faux, l'email entier est compté faux :
- Sans les règles métier, le modèle se laisse piéger par le **ton alarmiste** ou les montants élevés pour attribuer l'urgence.
- Il échoue sur les cas implicites (addition de deux devis, sélection du sinistre le plus urgent dans l'email à double sinistre, ou calcul exact des dates relatives).

### Pourquoi `v2` (Few-shot) chute à 0 % (100 % d'échec de format) ?
C'est l'enseignement technique le plus intéressant de l'expérience :
- Dans `v2.txt`, les exemples utilisent des marqueurs textuels (`Exemple 1 : ... Résultat :`). Par mimétisme, `llama3.2` préfixe ou commente sa réponse (par ex. en répétant `Résultat :` ou une phrase d'introduction avant l'accolade `{`).
- Or, notre fonction `nettoyer_texte()` a été conçue (et testée unitairement dans `test_dojo.py`) pour ne retirer **que** les balises de code Markdown ```` ```json ... ``` ````, et rejeter tout texte libre avant le JSON (`test_parser_reponse_invalide_renvoie_none[texte_avant_json]`).
- Conséquence : 100 % des réponses de `v2` sont rejetées au parsing avant même l'évaluation des champs. Cela démontre qu'un petit modèle 3B en *few-shot* imite la forme conversationnelle du prompt au détriment de la contrainte « JSON uniquement ».

### Ce que débloque `v3` (Prompt structuré)
L'ajout de règles métier explicites, de délimiteurs `<email>` et d'une consigne de formatage stricte en fin de prompt fait bondir toutes les métriques :
- Le taux de JSON valide monte à **93,3 %** (un seul échec de format sur 15).
- L'exactitude par champ progresse de **60,0 % à 70,0 %** (+10 points, soit 42 champs exacts sur 60).
- L'exactitude globale (les 4 champs justes simultanément sur un même email) **triple**, passant de **13,3 % (2/15) à 40,0 % (6/15)**.

---

## 7. Verdict final sur `llama3.2` (3B)

### Ce que `llama3.2` maîtrise
1. **Classification thématique (`type`)** : distinguer un sinistre `auto` d'un sinistre `habitation` est très bien réussi.
2. **Extraction directe** : lorsqu'un montant unique ou une date explicite figure dans le texte, l'extraction à `T=0` est stable.
3. **Respect du schéma JSON sous contrainte forte (`v3`)** : avec 93,3 % de réponses validées par Pydantic sans mode JSON forcé côté moteur, le modèle suit bien les contraintes structurelles quand elles sont placées en fin de prompt.

### Les limites rédhibitoires d'un modèle 3B sur cette tâche
1. **Calcul calendaire sur les dates relatives** : résoudre *« samedi dernier »* ou *« mardi »* par rapport à une `date_reception` demande de connaître le jour de la semaine correspondant à la date de réception et de soustraire le bon nombre de jours. Un modèle de 3B paramètres se trompe fréquemment d'un ou deux jours.
2. **Raisonnement multi-contraintes** : combiner simultanément l'addition de sous-totaux (`3 150 + 420`), l'exclusion de la franchise (`150 €`) et la hiérarchisation de deux sinistres dans un même mail dépasse souvent la capacité d'attention d'un modèle léger.
3. **Sensibilité au formatage du prompt (`v2`)** : le moindre indice conversationnel dans le prompt suffit à faire dérailler la sortie JSON brute.

### Verdict métier (Assurance)
> **Verdict : Insuffisant pour un traitement 100 % automatique en production (40 % de dossiers entièrement exacts), mais pertinent comme pré-remplissage assisté ou après couplage avec un modèle plus puissant.**
>
> En assurance, une erreur sur l'urgence retarde la prise en charge d'un sinistre grave, et une erreur sur le montant fausse le provisionnement. Avec 60 % de dossiers comportant au moins une erreur (souvent sur la date relative ou une nuance d'urgence), `llama3.2` (3B) ne peut pas alimenter directement le système de gestion sans validation humaine. En revanche, le *prompt engineering* structuré (`v3`) a prouvé son efficacité en **triplant le taux de dossiers parfaits (de 13,3 % à 40,0 %)** à coût matériel et API nul.

---

## 8. Limites du protocole et pistes d'amélioration

- **Parsing volontairement strict** : `nettoyer_texte` ne retire que les balises ```` ``` ````. En production, activer le paramètre natif `format=Sinistre.model_json_schema()` d'Ollama (Structured Outputs) éliminerait 100 % des erreurs de format (`v2` et les 6,7 % d'échec de `v3`).
- **Taille de l'échantillon** : 15 emails permettent de couvrir chaque piège unitairement (1 email = ~6,7 % du score global), mais un benchmark de production nécessiterait 100 à 200 emails pour réduire la variance.
- **Suite logique (Benchmark de modèles)** : exécuter exactement ce même script `dojo.py` et ce même `jeu_test.json` avec un modèle *frontier* via API (Claude Sonnet / GPT-4o) pour mesurer le gain de précision sur les dates relatives et les doubles sinistres face au coût en tokens.

---

## Phrase d'accroche CV

> *« Classification et extraction structurée de déclarations de sinistre par LLM (`llama3.2`, Pydantic, Pytest) : exactitude par champ portée de 60 % à 70 % et taux de dossiers 100 % conformes triplé (de 13,3 % à 40,0 %) par prompt engineering mesuré. »*
