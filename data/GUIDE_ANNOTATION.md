# Guide d'annotation — jeu_test.json

Règles appliquées pour remplir `attendu`. Toute nouvelle annotation doit les suivre,
sinon les scores ne sont plus comparables.

## Champs

| Champ | Valeurs | Règle |
|---|---|---|
| `type` | `auto` / `habitation` | Contrat concerné par le sinistre. |
| `date` | `AAAA-MM-JJ` ou `null` | Date de **survenance** du sinistre (pas la date de réception, de constat ou de devis). Date relative (« hier », « samedi dernier ») → résolue à partir de `date_reception`. Année absente → année de `date_reception`. Indéterminable au jour près → `null`. |
| `montant` | float (euros) ou `null` | **Somme** des montants chiffrés des dommages (devis, estimation, valeur volée). La franchise n'est **pas** un montant de dommage. Aucun montant → `null`. |
| `urgence` | `haute` / `moyenne` / `basse` | Voir ci-dessous. |

## Urgence

- **haute** : personne blessée ou en danger, sinistre **encore en cours** (fuite active, fumée), logement inhabitable ou non sécurisé, véhicule immobilisé ou indisponible.
- **moyenne** : situation stabilisée mais **risque d'aggravation** ou usage dégradé (protection provisoire, élément de sécurité touché, humidité/moisissure).
- **basse** : dommages stabilisés, sans impact sur la sécurité ni l'usage (esthétique, déjà réparé).

Le **ton** de l'email (énervé, paniqué) et le **montant** ne déterminent pas l'urgence.

## Plusieurs sinistres dans un email

`attendu` = le sinistre **le plus urgent** (à égalité : le premier cité).
Les autres vont dans `autres_sinistres` (même format), pour une future version multi-sinistres.

## Métadonnées

- `date_reception` : nécessaire pour résoudre les dates relatives.
- `style` et `pieges` : servent à l'analyse d'erreurs (score par type de piège).
