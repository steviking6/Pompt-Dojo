# Prompt-Dojo — Tri automatique de déclarations de sinistre

Évaluation et comparaison mesurée de trois stratégies de **prompt engineering** (**zero-shot**, **few-shot**, **prompt structuré**) et de deux architectures de modèles — un petit LLM local (**`llama3.2`** 3B via Ollama) face à un modèle *frontier* (**GPT** via API OpenAI) — pour extraire automatiquement les informations clés d'emails de déclaration de sinistre (`auto` / `habitation`) avec validation stricte par **Pydantic**.

---

## 1. Problème métier

Dans une compagnie d'assurance, les déclarations de sinistre arrivent par email sous des formes très hétérogènes : courriers formels, messages pressés, SMS bourrés de fautes d'orthographe, textes longs et émotionnels, ou encore déclarations multiples dans un même message.

Pour orienter automatiquement un dossier (ouverture de sinistre, missionnement d'un expert ou d'un dépanneur en urgence, provisionnement financier), il faut extraire de manière fiable **4 champs structurés** :
- `type` : contrat concerné (`"auto"` ou `"habitation"`)
- `date` : date exacte de **survenance** du sinistre (`"AAAA-MM-JJ"` ou `null`)
- `montant` : somme chiffrée des dommages en euros (`float` > 0 ou `null`)
- `urgence` : niveau de priorité opérationnelle (`"basse"`, `"moyenne"` ou `"haute"`)

**Objectif du projet** : mesurer rigoureusement, chiffres à l'appui sur un jeu de test annoté, jusqu'où le *prompt engineering* permet d'emmener un petit modèle local de 3 milliards de paramètres (`llama3.2`) comparé à un modèle *frontier* (`GPT`), et établir un verdict objectif sur leur utilisabilité en assurance.

---

## 2. Arborescence du projet

```text
Prompt-Dojo/
├── data/
│   ├── GUIDE_ANNOTATION.md  # règles métier de référence pour l'annotation
│   ├── jeu_test.json        # 15 emails de sinistre annotés avec cas pièges
│   ├── resultats_llama.csv  # scores mesurés pour llama3.2 (v1, v2, v3)
│   ├── resultats_gpt.csv    # scores mesurés pour GPT (v1, v2, v3)
│   └── comparaison.csv      # écarts de performance entre GPT et llama3.2
├── prompts/
│   ├── v1.txt               # zero-shot (consigne courte + clés attendues)
│   ├── v2.txt               # few-shot (2 exemples hors jeu de test)
│   └── v3.txt               # structuré (règles métier, schéma JSON, délimiteurs <email>)
├── src/
│   └── dojo.py              # modèle Pydantic, nettoyage, parsing, évaluation et comparaison
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

- **Modèles comparés** :
  - **`llama3.2`** (3B paramètres) exécuté en local via Ollama (`temperature = 0`).
  - **`GPT`** via l'API OpenAI (`reasoning_effort = "low"`, `temperature = 0`).
- **Validation** : nettoyage des éventuelles balises Markdown ```` ```json ```` via `nettoyer_texte()`, puis validation stricte du schéma et des types via `Sinistre.model_validate_json()` (Pydantic).
- **Les 3 versions testées** :
  1. **`v1` — Zero-shot** : consigne directe demandant un objet JSON avec les 4 clés et leurs types/valeurs autorisés, sans exemple ni explication des règles métier.
  2. **`v2` — Few-shot** : consigne accompagnée de 2 exemples complets (`Date de réception`, `Mail`, `Résultat : {...}`) hors jeu de test, illustrant un cas `"auto"` avec montant et un cas `"habitation"` avec `null`.
  3. **`v3` — Prompt structuré** : définition du rôle métier, règles d'extraction explicites point par point (dates relatives, somme des montants hors franchise, critères objectifs d'urgence, priorité au sinistre le plus urgent), délimiteurs `<email>...</email>`, consigne de sécurité anti-*prompt injection*, et obligation de répondre sur une seule ligne JSON brute.

---

## 5. Résultats mesurés et Comparaison (`llama3.2` vs `GPT`)

### 5.1 Scores de `llama3.2` (`data/resultats_llama.csv`)

| Version | Stratégie | JSON valide (%) | Échec de format (%) | Exactitude par champ (%) | Exactitude globale / email (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`v1`** | Zero-shot | 86,7 % *(13/15)* | 13,3 % *(2/15)* | 60,0 % *(36/60)* | 13,3 % *(2/15)* |
| **`v2`** | Few-shot | 0,0 % *(0/15)* | 100,0 % *(15/15)* | 0,0 % *(0/60)* | 0,0 % *(0/15)* |
| **`v3`** | Structuré | **93,3 %** *(14/15)* | **6,7 %** *(1/15)* | **70,0 %** *(42/60)* | **40,0 %** *(6/15)* |

### 5.2 Scores de `GPT` (`data/resultats_gpt.csv`)

| Version | Stratégie | JSON valide (%) | Échec de format (%) | Exactitude par champ (%) | Exactitude globale / email (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`v1`** | Zero-shot | 93,3 % *(14/15)* | 6,7 % *(1/15)* | 86,7 % *(52/60)* | 66,7 % *(10/15)* |
| **`v2`** | Few-shot | 93,3 % *(14/15)* | 6,7 % *(1/15)* | 90,0 % *(54/60)* | 80,0 % *(12/15)* |
| **`v3`** | Structuré | **100,0 %** *(15/15)* | **0,0 %** *(0/15)* | **100,0 %** *(60/60)* | **100,0 %** *(15/15)* |

### 5.3 Tableau comparatif des écarts (`data/comparaison.csv`)

| Version | JSON valide (`Llama` → `GPT`) | Exactitude champs (`Llama` → `GPT`) | Exactitude globale (`Llama` → `GPT`) | Modèle le plus performant (Gain global) |
| :--- | :---: | :---: | :---: | :---: |
| **`v1` (Zero-shot)** | 86,7 % → 93,3 % *(+6,6 pts)* | 60,0 % → 86,7 % *(+26,7 pts)* | 13,3 % → 66,7 % | **GPT (+53,4 %)** |
| **`v2` (Few-shot)** | 0,0 % → 93,3 % *(+93,3 pts)* | 0,0 % → 90,0 % *(+90,0 pts)* | 0,0 % → 80,0 % | **GPT (+80,0 %)** |
| **`v3` (Structuré)** | 93,3 % → 100,0 % *(+6,7 pts)* | 70,0 % → 100,0 % *(+30,0 pts)* | 40,0 % → 100,0 % | **GPT (+60,0 %)** |

---

## 6. Analyse des erreurs et de la comparaison

### 6.1 Pourquoi `v1` (Zero-shot) sépare déjà fortement les deux modèles (13,3 % vs 66,7 %) ?
- **`llama3.2`** respecte globalement le format JSON (13/15 valides) et identifie bien le `type` de contrat (`auto` vs `habitation`), ce qui lui assure 60,0 % de champs corrects. Mais sans les règles métier, il se laisse piéger par le **ton alarmiste** ou les montants élevés pour attribuer l'urgence, et échoue sur les dates relatives ou les calculs implicites (seulement 2/15 emails parfaits).
- **`GPT`** dispose d'une compréhension implicite beaucoup plus robuste dès le zero-shot : il atteint **86,7 %** d'exactitude par champ et **66,7 %** d'emails entièrement exacts (10/15, soit **+53,4 points** devant Llama), ne commettant d'erreurs que sur les arbitrages métier spécifiques à l'assurance qui n'ont pas encore été explicités dans le prompt.

### 6.2 Pourquoi `v2` (Few-shot) fait chuter `llama3.2` à 0 % alors que `GPT` grimpe à 80 % ?
C'est l'enseignement technique majeur de la comparaison :
- Dans `v2.txt`, les exemples utilisent des marqueurs textuels (`Exemple 1 : ... Résultat :`). Par mimétisme, **`llama3.2`** préfixe sa réponse (par ex. en répétant `Résultat :` avant `{`). Notre fonction `nettoyer_texte()` rejetant strictement tout texte libre hors balises Markdown ```` ```json ````, 100 % des réponses de `llama3.2` échouent au parsing.
- À l'inverse, **`GPT`** dissocie parfaitement la structure pédagogique des exemples de la consigne finale (« réponds uniquement en JSON ») : il maintient **93,3 % de JSON valide** et exploite les 2 exemples pour monter à **90,0 %** de champs exacts et **80,0 %** d'emails parfaits (**+80,0 points** d'écart avec Llama).

### 6.3 Ce que débloque `v3` (Prompt structuré) : plafonnement du 3B vs sans-faute de GPT
L'ajout de règles métier explicites, de délimiteurs `<email>` et d'une consigne de formatage stricte en fin de prompt fait progresser les deux modèles, mais révèle le plafond de verre de l'architecture 3B :
- Chez **`llama3.2`**, le taux de JSON valide monte à **93,3 %**, l'exactitude par champ passe à **70,0 %** (42/60) et l'exactitude globale **triple** pour atteindre **40,0 %** (6/15). Il reste néanmoins limité par le calcul calendaire des dates relatives (*« samedi dernier »*) et le raisonnement multi-contraintes (additionner deux devis tout en ignorant une franchise).
- Chez **`GPT`**, le prompt structuré `v3` élimine la totalité des ambiguïtés métier : il réalise un **100,0 % sur toute la ligne** (15/15 JSON valides, 60/60 champs exacts, 15/15 emails parfaits, soit **+60,0 points** au-dessus de Llama). Tous les pièges (dates relatives, montants à additionner, franchises distractrices, double sinistre, ton vs urgence) sont résolus sans aucune erreur.

---

## 7. Verdict final et Conclusion métier

### Bilan comparatif : `llama3.2` (Local 3B) vs `GPT` (API Frontier)

| Critère d'évaluation | `llama3.2` (3B local) | `GPT` (API OpenAI) |
| :--- | :--- | :--- |
| **Sensibilité au format (`v2`)** | Très fragile (0 % sur le few-shot à cause du mimétisme textuel) | Robuste (93,3 % à 100 % de JSON valide sur toutes les versions) |
| **Impact du Prompt Engineering (`v1` → `v3`)** | Fort levier : exactitude globale triplée (**13,3 % → 40,0 %**) | Levier décisif : passage de bon à parfait (**66,7 % → 100,0 %**) |
| **Calcul calendaire & multi-contraintes** | Limité (erreurs fréquentes d'1 à 2 jours ou d'addition) | Maîtrisé à **100 %** dès que les règles sont explicitées (`v3`) |
| **Coût & Confidentialité** | Gratuit, 100 % local (données sur site) | Coût à l'appel API, transit cloud |

### Conclusion et Recommandation d'architecture (Assurance)
> **1. Le Prompt Engineering (`v3`) est indispensable quel que soit le modèle :**
> Même un modèle *frontier* comme GPT plafonne à **66,7 %** en zero-shot (`v1`) parce qu'il ne peut pas deviner les règles internes de la compagnie d'assurance (ex. ignorer la franchise, prioriser le sinistre le plus urgent). La structuration du prompt (`v3`) lui fait gagner **+33,3 points** pour atteindre **100 %**. Sur `llama3.2`, ce même travail de prompt fait tripler la performance (**13,3 % → 40,0 %**).
>
> **2. Le modèle détermine le niveau d'automatisation en production :**
> - **`llama3.2` (3B) — Insuffisant pour de l'automatisation pure (40 % en `v3`)** : en assurance, 60 % de dossiers contenant au moins une erreur (date décalée, urgence mal évaluée) interdit un traitement sans supervision. Il reste pertinent uniquement comme **outil gratuit de pré-remplissage** pour assister un gestionnaire humain.
> - **`GPT` + Prompt `v3` — Prêt pour l'automatisation en production (100 % en `v3`)** : avec **60,0 points d'exactitude globale de plus que Llama** en `v3` et un sans-faute sur les 15 cas pièges (60/60 champs), le couple **GPT + Prompt structuré + validation Pydantic** offre la fiabilité requise pour le tri et l'ouverture automatique de dossiers de sinistre.

---

## 8. Limites du protocole et pistes d'amélioration

- **Parsing volontairement strict** : `nettoyer_texte` ne retire que les balises ```` ``` ````. En production, activer les *Structured Outputs* natifs d'Ollama (`format=Sinistre.model_json_schema()`) et d'OpenAI (`response_format`) éliminerait 100 % des erreurs de format résiduelles.
- **Taille de l'échantillon** : 15 emails permettent de couvrir chaque piège unitairement (1 email = ~6,7 % du score global), mais un benchmark de pré-production nécessiterait 100 à 200 emails pour confirmer la stabilité du 100 % de GPT à grande échelle.
- **Piste hybride (Routing)** : utiliser un modèle local léger pour les emails simples (déclaration unique, date explicite) et router les cas complexes (double sinistre, calculs multiples) vers GPT.

---

> *« Benchmark et optimisation par Prompt Engineering (Zero-shot, Few-shot, Structuré) de l'extraction JSON de sinistres (`llama3.2` vs `GPT`, Pydantic, Pytest) : exactitude globale triplée sur modèle local (13,3 % → 40 %) et portée à 100 % sur GPT (+60 pts vs Llama). »*
