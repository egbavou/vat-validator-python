# Recherche — règles par pays et API VIES

- **Date :** 2026-10-22
- **Objet :** préparer le plan d'implémentation de `egbavou/vat-number` (voir `docs/plans/2026-10-21-design.md`).
- **Portée :** les 27 pays de l'UE + `XI` (format et clé), `GB`, `CH` et `NO` (format, clé documentée), puis l'API REST de VIES.
- **Fixtures :** `tests/Fixtures/vies/` (66 fichiers, octets bruts tels que reçus).

## Méthode

- **Références croisées :**
  - `dragonbe/vies`, branche `master`, commit `d9193cb` du 2024-07-05 (dernier tag `2.3.2`), fichiers `src/Vies/Validator/*.php` lus en entier. Licence MIT.
  - `python-stdnum`, branche `master` (version `2.2`). Le comportement est décrit ici ; **aucun code n'est repris** (licence LGPL).
  - Une implémentation indépendante, écrite pour cette recherche à partir des sources ci-dessous et jetée ensuite. Elle a servi à produire les vecteurs invalides et à confirmer les échantillons officiels.
- **Source primaire principale :** le document du ministère autrichien des Finances, *Information über die Konstruktionsregeln der Umsatzsteuer-Identifikationsnummern (UID)*, état novembre 2020 ([PDF BMF](https://www.bmf.gv.at/dam/jcr:d6794f8f-d321-43df-9840-1a841f9bf5dc/BMF_UID_Konstruktionsregeln_Stand_November%202020.pdf)), appelé **« BMF »** ci-dessous.
  - Chaque État membre y a **autorisé la publication** de ses règles, par accord bilatéral, au format de la Commission. C'est la source la plus officielle disponible pour AT, BE, DE, DK, EE, FI, GB/XI, HU, IE, IT, LT, LU, NL, PL, PT, SE, SI et SK.
  - Ont **refusé la publication** : BG, CY, CZ, EL, ES, FR, HR, LV, MT, RO.
  - La FAQ VIES confirme : la Commission « ne peut divulguer ces algorithmes » (`vatFaq_resp11`, texte servi par `https://ec.europa.eu/taxation_customs/vies/rest-api/translations?lang=en`). Ce même fichier donne les **formats** officiels (`faq_label_XXformat`).
- **Appels VIES :**
  - le 2026-10-22 entre 01:00 et 01:28 UTC, environ 185 requêtes au total ;
  - au moins 1,2 s entre deux requêtes ;
  - au plus 3 tentatives par numéro : `POST`, `POST`, puis `GET` en dernier recours.
- **GB, CH, NO :** registres officiels (Brønnøysundregistrene, registre UID suisse). Pour GB, le registre HMRC n'était pas interrogeable sans authentification ; voir la section GB.

---

## 1. Résumé

1. **Clés de contrôle.**
   - **Source officielle publiée (BMF ou texte national) pour 21 préfixes :** AT, BE, DE, DK, EE, FI, HU, IE, IT, LT, LU, NL, PL, PT, SE, SI, SK, XI, GB, CH, NO. Pour HR, la loi renvoie à la norme ISO 7064.
   - **Sources secondaires seulement pour 9 pays :** BG, CY, CZ, EL, ES, FR, LV, MT, RO. Des fragments officiels existent pour certains d'entre eux : la lettre du DNI espagnol, le Luhn du SIREN, le rodné číslo tchèque et l'EGN bulgare (spécification TIN de la Commission).
2. **Vérification en direct.**
   - **Pays complètement vérifiés :** chaque pays de l'UE + `XI` a au moins 2 numéros réels confirmés valides par VIES le 2026-10-22.
   - Des sous-variantes réelles ont aussi été confirmées :
     - BE commençant par `1` ;
     - FR à clé alphanumérique (`FR0W314684960`) et FR de Monaco ;
     - IE ancien format (`IE8F52100V`) et nouveau format à 9 caractères ;
     - LT à 12 chiffres ;
     - CZ groupe TVA (`699…`) ;
     - CY d'un organisme public (`9…`).
3. **Endpoint recommandé : `POST /check-vat-number`.**
   - C'est le seul des deux qui figure dans le contrat OpenAPI officiel.
   - Il renvoie les erreurs dans une enveloppe explicite (`actionSucceed: false`).
   - Le piège du `GET` est confirmé : `"isValid": false` avec `"userError": "MS_MAX_CONCURRENT_REQ"`, et aussi avec `"userError": "INVALID_INPUT"`.
4. **Surprises qui touchent la conception** (détail en section 4 et 5) :
   - **`FR44732829320` n'est pas valide dans VIES** (réponse `valid: false` le 2026-10-22 à 01:27:22 UTC).
     - Le document de conception l'utilise comme exemple de `Found` et comme exemple de `requester`.
     - Il passe pourtant le format, la clé et le Luhn : c'est un bon exemple de `NotFound`, pas de `Found`.
   - **Monaco :** les numéros français de Monaco (`FRxx000……`) sont valides dans VIES mais **leur « SIREN » ne passe pas Luhn** (`FR73000042183`, SAM Monaco Telecom).
     - La règle 3.2.4 du document (« le SIREN doit aussi passer Luhn ») doit exclure les SIREN commençant par `000`.
   - **Latence :** VIES a mis jusqu'à **11,8 s** pour répondre à un numéro valide (DK, CZ). Le `timeout` par défaut de 10 s produirait de faux `Transport`. Je recommande 30 s.
   - **Erreurs VIES en HTTP 200 :** les erreurs des États membres (`MS_MAX_CONCURRENT_REQ`, `INVALID_INPUT`…) arrivent en **HTTP 200**.
     - Les erreurs de saisie de la passerelle (`VOW-ERR-11`, `VOW-ERR-2500`, `VOW-ERR-2600`) arrivent en **HTTP 400**, avec le même JSON.
     - Un JSON mal formé ou un `Content-Type` absent produit **HTTP 500** `VOW-ERR-1`.
   - **Préfixe dans `vatNumber` :** envoyer `vatNumber: "LU20260743"` avec `countryCode: "LU"` renvoie **`valid: false` sans erreur**, donc un faux `NotFound`. Le numéro doit être envoyé **sans** préfixe.
   - **Champs `name` et `address` :** le marqueur d'absence n'est pas toujours `---`.
     - `""` pour la plupart des numéros invalides ;
     - `---` pour DE et ES, même quand le numéro est valide ;
     - `N/A` pour l'adresse en LT.
     - Les adresses contiennent des `\n` en tête, en fin ou en double, et des suites d'espaces. EL sépare les noms par `||` et BT par `!!`.
   - **`requestIdentifier`** vaut `""` (chaîne vide, pas `null` ni absent) sans requester.
     - VIES a émis un identifiant pour un requester fictif mais bien formé (`IE0000000W`). Il ne contrôle donc que la syntaxe du requester.
   - **`NO974760673`** (exemple du document) est un numéro d'organisation valide, mais **pas inscrit au registre de la TVA** (`registrertIMvaregisteret: false`). Il reste valable comme exemple hors ligne.
   - **Règles officielles contre bibliothèques :** plusieurs règles officielles divergent de dragonbe et de stdnum : suffixe SE, plages GB, reste 10 NL, office IT, `10` en tête en EE. Le détail est donné par pays.
   - **`FailureReason`** n'a pas de cas pour les règles de structure (premier chiffre interdit, code de bureau IT, `10` imposé en EE, 8e chiffre LT…). Voir section 5.

---

## 2. Tableau récapitulatif

Regex appliquées à la **partie nationale** (après nettoyage, en majuscules, préfixe retiré). « BMF » renvoie au PDF cité plus haut.

| Préfixe | Regex (partie nationale) | Longueurs | Algorithme en une ligne | Source |
|---|---|---|---|---|
| AT | `^U\d{8}$` | 9 | Luhn modifié sur C2…C8, `C9 = (10 − (R + C2+C4+C6+C8 + 4) mod 10) mod 10` | BMF (primaire) |
| BE | `^[01]\d{9}$` | 10 | `C9C10 = 97 − (C1…C8 mod 97)` | BMF + SPF Économie (primaires) |
| BG | `^\d{9,10}$` | 9, 10 | 9 : poids 1–8 puis 3–10, mod 11 ; 10 : EGN, LNCh ou « autre » | Spéc. TIN CE (EGN) ; reste secondaire |
| CY | `^\d{8}[A-Z]$`, sans `12` en tête | 9 | Table de transcodage sur rangs impairs, somme mod 26 → lettre | Spéc. TIN CE (même algorithme) ; secondaire |
| CZ | `^\d{8,10}$` | 8, 9, 10 | 8 : poids 8–2 mod 11 ; `6……` (9) : table ; rodné číslo : date + mod 11 | Loi 133/2000 (RČ) ; reste secondaire |
| DE | `^[1-9]\d{8}$` | 9 | ISO 7064 MOD 11,10 | BMF (primaire) |
| DK | `^[1-9]\d{7}$` | 8 | Somme pondérée 2,7,6,5,4,3,2,1 divisible par 11 | BMF + Erhvervsstyrelsen (primaires) |
| EE | `^10\d{7}$` | 9 | Poids 3,7,1… ; `C9 = arrondi_sup(A1, 10) − A1` | BMF (primaire) |
| EL | `^\d{9}$` | 9 | Poids 2⁸…2¹, `(S mod 11) mod 10` | Secondaire seulement |
| ES | `^[0-9A-Z]\d{7}[0-9A-Z]$`, extrémités pas toutes deux numériques | 9 | DNI/NIE/KLM : mod 23 → lettre ; CIF : Luhn → chiffre ou lettre `JABCDEFGHI` | Textes BOE (structure) ; algorithme CIF secondaire |
| FI | `^\d{8}$` | 8 | Poids 7,9,10,5,8,4,2 ; `r = 0 → 0`, `r = 1 → invalide`, sinon `11 − r` | Décret 288/2001 + BMF (primaires) |
| FR | `^[0-9A-HJ-NP-Z]{2}\d{9}$` | 11 | Clé numérique `(12 + 3 × (SIREN mod 97)) mod 97` ; clé alphanumérique : formule mod 11 ; SIREN Luhn sauf Monaco | INSEE (Luhn) ; clés : secondaire |
| HR | `^\d{11}$` | 11 | ISO 7064 MOD 11,10 | Loi OIB + Pravilnik (primaires) |
| HU | `^\d{8}$` | 8 | Poids 9,7,3,1,9,7,3 ; `(10 − S mod 10) mod 10` | BMF (primaire) |
| IE | `^\d{7}[A-W][A-I]?$` ou `^\d[A-Z+*]\d{5}[A-W]$` | 8, 9 | Poids 8…2 (+ 9 × lettre 9), mod 23 → `WABC…V` | BMF (primaire) |
| IT | `^\d{11}$` | 11 | Luhn ; matricule ≠ 0 ; bureau 001–100, 120, 121, 888, 999 | DM 23/12/1976 + BMF (primaires) |
| LT | `^\d{7}1\d$` ou `^\d{10}1\d$` | 9, 12 | Poids 1…9,1,2 mod 11 ; si 10, poids 3…9,1,2,3,4 ; si 10 → 0 | BMF (primaire) |
| LU | `^\d{8}$` | 8 | `C7C8 = C1…C6 mod 89` | BMF (primaire) |
| LV | `^\d{11}$` | 11 | Personne morale (C1 > 3) : somme pondérée ≡ 3 mod 11 ; personne physique : code personnel | Secondaire seulement |
| MT | `^[1-9]\d{7}$` | 8 | `C7C8 = 37 − (S mod 37)`, poids 3,4,6,7,8,9 | Secondaire seulement |
| NL | `^\d{9}B\d{2}$` (mod 11) ; `^[0-9A-Z+*]{9}B\d{2}$` (mod 97) | 12 | Mod 11 (« 11-proef ») d'abord, sinon ISO 7064 MOD 97-10 sur `NL` + numéro | BMF (primaire) |
| PL | `^\d{10}$` | 10 | Poids 6,5,7,2,3,4,5,6,7 mod 11 ; 10 → invalide | BMF (primaire) |
| PT | `^[1-9]\d{8}$` | 9 | `R = 11 − (poids 9…2) mod 11` ; 10, 11 → 0 | BMF (primaire) |
| RO | `^[1-9]\d{1,9}$` | 2 à 10 | Clé 7,5,3,2,1,7,5,3,2 (aligné à droite) ; `(10 × S) mod 11`, 10 → 0 | Secondaire seulement |
| SE | `^\d{10}(0[1-9]\|[1-8]\d\|9[0-4])$` | 12 | Luhn sur C1…C10 ; suffixe 01–94 (BMF) ou toujours 01 (Skatteverket) | BMF + Skatteverket (primaires, en désaccord) |
| SI | `^[1-9]\d{7}$` | 8 | `R = 11 − (poids 8…2) mod 11` ; 10 → 0 ; 11 → invalide | BMF (primaire) |
| SK | `^[1-9]\d[2-47-9]\d{7}$` | 10 | Nombre entier divisible par 11 | BMF (primaire) |
| XI | `^(\d{9}\|\d{12}\|GD\d{3}\|HA\d{3})$` | 5, 9, 12 | Poids 8…2 + C8C9, mod 97 ou mod 97 « 9755 », avec plages | BMF (primaire) |
| GB | identique à XI | 5, 9, 12 | identique à XI | BMF (primaire) |
| CH | `CHE` + `^\d{9}$` (+ `MWST`, `TVA`, `IVA`) | 9 chiffres | Poids 5,4,3,2,7,6,5,4 ; `11 − r` ; 11 → 0 ; 10 → jamais attribué | eCH-0097 (primaire) |
| NO | `^\d{9}$` (+ `MVA`) | 9 | Poids 3,2,7,6,5,4,3,2 ; `11 − r` ; 11 → 0 ; 10 → invalide | Brønnøysundregistrene (primaire) |

---

## 3. Règles par pays

**Conventions de cette section :**
- `Ci` est le i-ème caractère de la partie nationale, en partant de 1.
- `S` est une somme pondérée.
- « dragonbe » désigne `DragonBe\Vies\Validator\ValidatorXX::validate()`, qui reçoit la partie nationale après `Vies::filterVat()` (retrait des espaces, points et tirets).
- Dans les colonnes « dragonbe » et « stdnum », `oui` veut dire que la bibliothèque **accepte** le numéro.
- **Raisons attendues :** elles reprennent `FailureReason`. « Structure » désigne une règle de structure qui n'a pas encore de cas dédié (voir section 5).
- **Vecteurs valides :** tous ont été confirmés le **2026-10-22** par `POST /check-vat-number`, réponse `"valid": true`.
  - L'heure est celle du champ `requestDate` (UTC).
  - Le nom est celui renvoyé par VIES, ou `---` quand l'État ne le communique pas.

### AT — Autriche

- **Format :** `U` + 8 chiffres ; C9 est la clé. VIES : `ATU99999999`, note 1 : le premier caractère est toujours `U`.
- **Algorithme (BMF) :**
  1. Pour i = 3, 5, 7 : `Si = floor(Ci / 5) + (2 × Ci) mod 10`. C'est la somme des chiffres de `2 × Ci`.
  2. `R = S3 + S5 + S7`.
  3. `C9 = (10 − (R + C2 + C4 + C6 + C8 + 4) mod 10) mod 10`.
  4. Échantillon officiel : `U10223006`.
- **Source :** BMF, page 1 (primaire).
- **Écarts :** aucun sur la clé.
  - dragonbe calcule `96 − somme` et garde le dernier chiffre, ce qui est équivalent.
  - stdnum calcule `(6 − luhn.checksum) mod 10`, ce qui est aussi équivalent.
  - dragonbe ne vérifie pas que C2…C9 sont des chiffres : il convertit avec `(int)`, et une lettre compte pour 0. stdnum le vérifie (`isdigits`).

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `ATU15361506` | Erste Group Bank AG | 01:07:30 |
| `ATU14703908` | VERBUND AG | 01:07:31 |
| `ATU62895905` | A1 Telekom Austria Aktiengesellschaft | 01:07:32 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `ATU62895906` | clé +1 | `InvalidChecksum` | non | non |
| `ATU6289590` | 8 caractères | `InvalidLength` | non | non |
| `ATX62895905` | `X` au lieu de `U` | `InvalidCharacters` | non | non |

### BE — Belgique

- **Format :** 10 chiffres.
  - **Jusqu'au 31/12/2019 :** C1 = `0` et C2 de 1 à 9.
  - **Depuis le 01/01/2020 :** C1 = `0` ou `1` (BMF).
  - Le premier numéro de la série `1` a été attribué le **19 septembre 2023** ([SPF Économie, 22/09/2023](https://news.economie.fgov.be/228779-les-numeros-d-entreprise-passent-au-1/)).
  - Les anciens numéros à 9 chiffres prennent un `0` devant (note 3 de la FAQ VIES).
- **Algorithme (BMF) :**
  1. `N = int(C1…C8)`.
  2. `C9C10 = 97 − (N mod 97)`. Le résultat va de 01 à 97 ; il n'est jamais 00.
  3. Échantillon officiel : `0776091951`.
- **Source :** BMF, page 2 (primaire). Aucun texte de loi belge consulté ne décrit le mod 97.
- **Écarts :**
  - dragonbe ne contrôle pas le premier chiffre : `BE2123456791` est accepté.
  - stdnum le refuse (`InvalidComponent`) et complète les saisies à 9 chiffres avec un `0`.
  - **Décision à prendre :** accepter ou non la saisie à 9 chiffres en la complétant. VIES le fait lui-même : le champ `originalVatNumber` du `GET` montre que VIES « corrige » parfois le numéro.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `BE0417497106` | NV Anheuser-Busch InBev | 01:00:38 |
| `BE0403170701` | SA ELECTRABEL | 01:07:37 |
| `BE0403199702` | SA BNP Paribas Fortis | 01:07:41 |
| `BE0202239951` | SA DPU PROXIMUS | 01:07:48 (2e essai) |
| `BE1010783451` | GEMEENTE Gemeente Beveren-Kruibeke-Zwijndrecht (série `1`) | 01:16:08 |
| `BE1018387657` | BV Group Van Elsen Cargo Care (série `1`) | 01:16:11 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `BE0417497107` | clé +1 | `InvalidChecksum` | non | non |
| `BE041749710` | 9 chiffres | `InvalidLength` (ou `InvalidChecksum` si l'on complète avec un `0`) | non | non |
| `BE2123456791` | premier chiffre `2`, clé juste | Structure | **oui** | non |

### BG — Bulgarie

- **Format :** 9 chiffres (personnes morales, EIK/BULSTAT) ou 10 chiffres (personnes physiques et autres). VIES : `BG999999999 or BG9999999999`.
- **Algorithme :**
  - **9 chiffres :**
    1. `S1 = 1·C1 + 2·C2 + … + 8·C8`, puis `r = S1 mod 11`.
    2. Si `r = 10` : `S2 = 3·C1 + 4·C2 + … + 10·C8`, puis `r = S2 mod 11`. Si `r = 10` encore, `r = 0`.
    3. Valide si `C9 = r`.
  - **10 chiffres :** valide si **l'une** des trois règles passe. Rien dans le numéro n'indique son type.
    1. **EGN** (citoyen) :
       - poids 2,4,8,5,10,9,7,3,6 sur C1…C9 ;
       - `C10 = (S mod 11) mod 10` ;
       - **et** C1…C6 doit former une date valide AAMMJJ. Un mois de 21 à 32 signifie les années 1800 ; de 41 à 52, les années 2000.
    2. **LNCh** (étranger) : poids 21,19,17,13,11,9,7,3,1 ; `C10 = S mod 10`.
    3. **Autre** : poids 4,3,2,7,6,5,4,3,2 ; `R = 11 − (S mod 11)`. `R = 11 → 0` ; `R = 10 → invalide` ; sinon `C10 = R`.
- **Sources :**
  - La Bulgarie a refusé la publication (BMF).
  - L'EGN est décrit dans la spécification de la Commission *TIN Algorithms – Public – Functional Specification* v5.03 (DG TAXUD, 2017, [copie archivée](https://web.archive.org/web/20230612064355id_/https://ec.europa.eu/taxation_customs/tin/specs/FS-TIN%20Algorithms-Public.docx)).
  - Le 9 chiffres, le LNCh et le type « autre » ne s'appuient que sur des sources secondaires (braemoor, archive ; stdnum).
- **Écarts :**
  - dragonbe ne contrôle pas la date de l'EGN.
  - Pour le LNCh, il réutilise une fonction générique qui bascule sur d'autres poids quand `S mod 11 = 10`. Résultat : `BG1234560034`, un LNCh juste, est refusé par dragonbe et accepté par stdnum.
  - dragonbe ignore le type « autre » : `BG9999999996` est refusé par dragonbe et accepté par stdnum.
- **Vecteurs réels à 10 chiffres :** ce sont des personnes physiques. Je n'en ai volontairement pas cherché (données personnelles). Vecteurs synthétiques : `BG7501011232` (EGN), `BG1234567893` (LNCh), `BG9999999996` (autre).

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `BG812114069` | ЛУКОЙЛ Нефтохим Бургас - АД | 01:07:49 |
| `BG831642181` | Виваком България - ЕАД | 01:07:50 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `BG831642182` | clé +1 | `InvalidChecksum` | non | non |
| `BG83164218` | 8 chiffres | `InvalidLength` | non | non |
| `BG83164218100` | 11 chiffres | `InvalidLength` | non | non |

### CY — Chypre

- **Format :** 8 chiffres + 1 lettre de contrôle. VIES : `CY99999999L`.
- **Premier chiffre :** les sources divergent.
  - stdnum : tout sauf le préfixe `12`.
  - dragonbe : `0,1,3,4,5,6,9`, sans `12`.
  - braemoor : `0–5` et `9`.
  - Spécification TIN de la CE (2017) : `0` ou `9` pour les personnes physiques.
  - Fiche TIN de la CE (2023) : `0`, `6` ou `9`.
  - Selon un avis du Département des impôts chypriote (*New TIN Format 04052023*), les **nouveaux TIC commencent par `6` depuis le 27/03/2023**. Je n'ai pas pu ouvrir cet avis (redirection) : **non vérifié**.
  - Observé dans VIES : les sociétés commencent par `10`, les organismes publics par `90`.
- **Algorithme :**
  1. Rangs impairs (C1, C3, C5, C7) : remplacer le chiffre selon la table `0→1, 1→0, 2→5, 3→7, 4→9, 5→13, 6→15, 7→17, 8→19, 9→21`.
  2. Rangs pairs (C2, C4, C6, C8) : prendre le chiffre tel quel.
  3. `S` = somme des huit valeurs ; `C9 = lettre(65 + S mod 26)`, de `A` à `Z`.
- **Sources :**
  - Chypre a refusé la publication (BMF).
  - L'algorithme est identique à celui du TIC chypriote dans la spécification TIN de la CE (document officiel, mais pour le TIN et non la TVA).
  - L'exclusion de `12` n'a **aucune source trouvée**. Elle vient probablement de la spécification VIES non publique.
- **Écarts :**
  - **dragonbe ne vérifie pas du tout la lettre de contrôle** : `CY10137520F` est accepté.
  - Sur le premier chiffre, voir plus haut. Recommandation : ne restreindre que `12`, comme stdnum, pour ne pas rejeter les nouveaux numéros en `6`.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `CY10137520E` | CABLENET COMMUNICATION SYSTEMS PLC | 01:15:26 |
| `CY10083353J` | EUROPEAN UNIVERSITY-CYPRUS LTD | 01:15:28 |
| `CY90001673W` | ΠΑΝΕΠΙΣΤΗΜΙΟ ΚΥΠΡΟΥ (Université de Chypre) | 01:15:27 |

- **Numéros non retenus :** les numéros de démonstration de stdnum (`CY10259033P`, `CY10263870R`…) sont **invalides dans VIES** aujourd'hui.

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `CY10137520F` | lettre +1 | `InvalidChecksum` | **oui** | non |
| `CY1013752E` | 7 chiffres + lettre | `InvalidLength` | non | non |
| `CY12000000X` | préfixe `12` | Structure (source inconnue) | non | non |

### CZ — Tchéquie

- **Format :** 8, 9 ou 10 chiffres. VIES : `CZ99999999 or CZ999999999 or CZ9999999999`.
- **Algorithme :**
  - **8 chiffres (personne morale, IČO) :**
    1. `C1 ≠ 9` (règle stdnum ; sans source primaire).
    2. `S = 8·C1 + 7·C2 + … + 2·C7`, puis `r = S mod 11`.
    3. `c = 11 − r`. Si `c = 11`, `C8 = 1` ; si `c = 10`, `C8 = 0` ; sinon `C8 = c`.
  - **9 chiffres commençant par `6`** (« VČP » : personnes sans rodné číslo, et **groupes TVA `699…`**) :
    1. `S = 8·C2 + 7·C3 + … + 2·C8`, puis `r = S mod 11` et `d = 11 − r` (si `r = 0`, `d = 11`).
    2. `C9 = [8,7,6,5,4,3,2,1,0,9,8][d − 1]`.
  - **9 chiffres sans `6` en tête (rodné číslo d'avant 1954) :**
    - pas de clé ;
    - C1…C6 doit former une date AAMMJJ valide, avec le mois augmenté de 50 pour les femmes ;
    - année ≤ 53.
  - **10 chiffres (rodné číslo depuis 1954) :**
    - date AAMMJJ valide (mois +50 pour les femmes, +20 ou +70 depuis 2004) ;
    - le nombre entier est divisible par 11.
    - **Exception :** pour les numéros anciens, si `C1…C9 mod 11 = 10`, alors `C10 = 0`. Elle est connue mais absente de la loi.
- **Sources :**
  - **Rodné číslo :** loi 133/2000 Sb., § 13 ([zakonyprolidi.cz](https://www.zakonyprolidi.cz/cs/2000-133)), primaire.
  - **VČP :** l'administration fiscale tchèque déclare en 2026 que sa construction « n'est pas publiée » ([réponse à une demande d'accès, docx](https://financnisprava.gov.cz/assets/cs/prilohy/fs-generalni-financni-reditelstvi/Informace_106_2026_76.docx)).
  - **IČO :** sources secondaires seulement.
  - La Tchéquie a refusé la publication (BMF).
- **Écarts dragonbe :**
  - 8 chiffres : `C1 = 9` n'est pas refusé (`CZ90177045` accepté).
  - 10 chiffres : il somme les paires de chiffres mod 11, ce qui équivaut à la divisibilité, mais sans l'exception « reste 10 → 0 ».
  - Son contrôle d'année dépend de la date du jour.
- **Remarque :** la réponse VIES pour un groupe a pour nom `Group registration - This VAT ID corresponds to a Group of Taxpayers`, et pour adresse une URL. C'est à rendre tel quel.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `CZ00177041` | Škoda Auto a.s. | 01:08:10 |
| `CZ60193336` | O2 Czech Republic a.s. | 01:11:24 |
| `CZ699004742` | Group registration (Řízení letového provozu ČR, groupe TVA) | 01:17:07 (2e essai) |

- **Numéros non confirmés :**
  - `CZ45274649` (ČEZ) : 3 × `MS_MAX_CONCURRENT_REQ`, donc non confirmé.
  - `CZ45317054` (Komerční banka) : `valid: false`, probablement remplacé par un numéro de groupe.

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `CZ00177042` | clé +1 | `InvalidChecksum` | non | non |
| `CZ0017704` | 7 chiffres | `InvalidLength` | non | non |
| `CZ90177045` | 8 chiffres commençant par `9` | Structure | **oui** | non |

### DE — Allemagne

- **Format :** 9 chiffres, `C1 > 0`.
- **Algorithme (BMF ; c'est ISO/IEC 7064 MOD 11,10) :**
  1. `P = 10`.
  2. Pour N = 1 à 8 :
     - `S = CN + P` ;
     - `M = S mod 10`, et si `M = 0`, `M = 10` ;
     - `P = (2 × M) mod 11`.
  3. `R = 11 − P`. Si `R = 10`, `C9 = 0` ; sinon `C9 = R`. `P` n'est jamais nul.
  4. Échantillon officiel : `111111125`.
- **Sources :**
  - BMF, page 3 (primaire).
  - Le BZSt ne publie que le format (« neun, nur Ziffern »).
- **Écarts :** dragonbe applique le même calcul, mais sans contrôler `C1 > 0` ni les caractères : `DE012345679` est accepté. stdnum le refuse.
- **Remarque VIES :** l'Allemagne ne communique **ni nom ni adresse** : `"name" : "---"`, `"address" : "---"`, même pour un numéro valide. L'identité des titulaires ci-dessous vient donc des mentions légales des entreprises, pas de VIES.

| Numéro valide | Titulaire (hors VIES) | Heure UTC |
|---|---|---|
| `DE129274202` | Siemens AG ([mentions légales Siemens](https://www.siemens.com/cn/zh/general/legal.html)) | 01:08:22 |
| `DE123475223` | Deutsche Telekom AG ([telekom.com/imprint](https://www.telekom.com/imprint)) | 01:08:24 |
| `DE115235681` | Volkswagen AG (attribution non revérifiée) | 01:08:25 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `DE129274203` | clé +1 | `InvalidChecksum` | non | non |
| `DE12927420` | 8 chiffres | `InvalidLength` | non | non |
| `DE012345679` | `C1 = 0`, clé juste | Structure | **oui** | non |

### DK — Danemark

- **Format :** 8 chiffres, `C1 > 0`. VIES l'affiche en 4 blocs de 2.
- **Algorithme (BMF) :**
  1. `R = 2·C1 + 7·C2 + 6·C3 + 5·C4 + 4·C5 + 3·C6 + 2·C7 + 1·C8`.
  2. Valide si `R mod 11 = 0`.
  3. Échantillon officiel : `88146328`.
- **Sources :**
  - BMF, page 4.
  - Erhvervsstyrelsen, page « modulus 11 » ([archive 2014](https://web.archive.org/web/20141027174421id_/http://erhvervsstyrelsen.dk/modulus_11)). Elle précise : reste 1 → numéro jamais attribué ; reste 0 → clé 0.
- **Écarts :** dragonbe ne contrôle pas `C1 > 0` (`DK00000000` accepté) ; stdnum le refuse.
- **Remarque VIES :** l'adresse DK se termine par `\n`.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `DK24256790` | NOVO NORDISK A/S | 01:08:38 |
| `DK22756214` | A.P. MØLLER - MÆRSK A/S | 01:08:49 |
| `DK61056416` | Carlsberg A/S | 01:09:01 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `DK24256791` | clé +1 | `InvalidChecksum` | non | non |
| `DK2425679` | 7 chiffres | `InvalidLength` | non | non |
| `DK00000000` | `C1 = 0` | Structure | **oui** | non |

### EE — Estonie

- **Format :** 9 chiffres ; **C1C2 = `10`** (BMF).
- **Algorithme (BMF) :**
  1. `A1 = 3·C1 + 7·C2 + 1·C3 + 3·C4 + 7·C5 + 1·C6 + 3·C7 + 7·C8`.
  2. `C9 = arrondi_sup(A1 à la dizaine) − A1`, soit `(10 − A1 mod 10) mod 10`.
  3. Échantillon officiel : `100207415`.
- **Source :** BMF, page 22 (primaire). L'EMTA ne donne que le format.
- **Écarts :** ni dragonbe ni stdnum n'imposent `10` en tête : `EE200070005` est accepté par les deux.
- **Origine des numéros ci-dessous :** registre du commerce estonien, par exemple [ariregister.rik.ee/eng/company/10234957](https://ariregister.rik.ee/eng/company/10234957) et [ariregister.rik.ee/eng/company/10421629](https://ariregister.rik.ee/eng/company/10421629).

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `EE100070008` | Telia Eesti AS | 01:12:45 |
| `EE100366327` | Eesti Energia AS (Representative of VAT Group) | 01:12:43 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `EE100070009` | clé +1 | `InvalidChecksum` | non | non |
| `EE10007000` | 8 chiffres | `InvalidLength` | non | non |
| `EE200070005` | ne commence pas par `10`, clé juste | Structure | **oui** | **oui** |

### EL — Grèce

- **Format :** 9 chiffres ; préfixe `EL`, jamais `GR`. **VIES répond `INVALID_INPUT` à `countryCode: "GR"`** (observé) : la conversion `GR → EL` du document de conception est indispensable.
- **Algorithme :**
  1. `S = 256·C1 + 128·C2 + 64·C3 + 32·C4 + 16·C5 + 8·C6 + 4·C7 + 2·C8`.
  2. `C9 = (S mod 11) mod 10`.
- **Sources :**
  - **Secondaires seulement.** La Grèce a refusé la publication (BMF) ; la spécification TIN de la CE indique « Not publicly available ».
  - dragonbe, stdnum et braemoor concordent.
- **Écarts :** stdnum complète les numéros à 8 chiffres avec un `0` devant (anciens AFM). Le format VIES et dragonbe n'admettent que 9 chiffres. Ainsi `EL09401924` est accepté par stdnum par coïncidence.
- **Remarque VIES :** les noms contiennent `||` comme séparateur (`…ΑΝΩΝΥΜΗ ΕΤΑΙΡΕΙΑ||ΟΤΕ`) et les adresses des suites d'espaces.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `EL094019245` | ΟΡΓΑΝΙΣΜΟΣ ΤΗΛΕΠΙΚΟΙΝΩΝΙΩΝ ΤΗΣ ΕΛΛΑΔΟΣ ΑΝΩΝΥΜΗ ΕΤΑΙΡΕΙΑ\|\|ΟΤΕ | 01:09:28 |
| `EL090000045` | ΔΗΜΟΣΙΑ ΕΠΙΧΕΙΡΗΣΗ ΗΛΕΚΤΡΙΣΜΟΥ ΑΝΩΝΥΜΗ ΕΤΑΙΡΙΑ\|\|ΔΕΗ ΑΕ ΔΕΗ | 01:09:30 |
| `EL094014201` | ΤΡΑΠΕΖΑ ΕΘΝΙΚΗ ΤΗΣ ΕΛΛΑΔΟΣ ΑΝΩΝΥΜΗ ΕΤΑΙΡΕΙΑ | 01:09:31 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `EL094019246` | clé +1 | `InvalidChecksum` | non | non |
| `EL09401924` | 8 chiffres | `InvalidLength` | non | **oui** (complété) |
| `EL0940192450` | 10 chiffres | `InvalidLength` | non | non |

### ES — Espagne

- **Format :** 9 caractères. Le premier et le dernier peuvent être des lettres ou des chiffres, **mais pas tous les deux des chiffres** (note 4 de la FAQ VIES : `ESX9999999X`).
- **Sous-variantes et algorithmes :**
  - **DNI** (citoyens) : 8 chiffres + lettre `TRWAGMYFPDXBNJZSQVHLCKE[n mod 23]`, où n est le nombre à 8 chiffres.
  - **NIE** (étrangers) : `X`, `Y` ou `Z` + 7 chiffres + lettre. On remplace la lettre de tête par `0`, `1` ou `2`, puis on applique la règle du DNI au nombre à 8 chiffres obtenu.
  - **K, L, M** (Espagnols de moins de 14 ans, Espagnols résidant à l'étranger, étrangers sans NIE) : lettre + 7 chiffres + lettre. La règle du DNI s'applique aux 7 chiffres.
  - **CIF** (personnes morales) : lettre de tête parmi `A B C D E F G H J N P Q R S U V W` + 7 chiffres D1…D7 + caractère de contrôle.
    1. `A = D2 + D4 + D6`.
    2. `B` = somme, pour D1, D3, D5 et D7, des chiffres de `2 × Di`.
    3. `d = (10 − (A + B) mod 10) mod 10`.
    4. Le contrôle vaut soit le chiffre `d`, soit la lettre `JABCDEFGHI[d]`.
- **Forme du caractère de contrôle CIF :** chiffre ou lettre ? Les sources divergent ; **aucune source primaire**.
  - es.wikipedia : lettre obligatoire pour `P Q R S W N` ; chiffre pour `A B E H` ; les deux possibles pour les autres.
  - stdnum : chiffre ou lettre pour toutes les entités.
  - dragonbe : lettre admise pour `A–H, N, P, Q, R, S, W`, chiffre pour `A–H, J, U, V`. dragonbe refuse donc `ESJ0123456F`, que les deux autres acceptent.
  - **Recommandation :** rester permissif comme stdnum (pas de faux rejet ; VIES tranche en ligne).
- **Sources :**
  - Orden EHA/451/2008, arts. 2 à 5 ([BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2008-3580)) : lettres des entités, sans algorithme.
  - RD 1065/2007, arts. 19 et 20 ([BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2007-15984)) : DNI, K, L, M.
  - Orden INT/2058/2008 ([BOE](https://boe.es/boe/dias/2008/07/15/pdfs/A30880-30881.pdf)) : NIE X puis Y, Z.
  - Lettre du DNI : page du ministère de l'Intérieur (protégée par Cloudflare, non ouverte) ; même règle dans la spécification TIN de la CE.
  - L'Espagne a refusé la publication de l'algorithme TVA (BMF).
- **Remarque VIES :** l'Espagne ne renvoie ni nom ni adresse (`---`), même pour un numéro **invalide** (`post-invalid-es-placeholder-name.json`). L'identité ci-dessous est celle des CIF publics de ces entités, pas une donnée VIES.

| Numéro valide | Titulaire (hors VIES) | Heure UTC |
|---|---|---|
| `ESA28015865` | Telefónica, S.A. | 01:09:32 |
| `ESA39000013` | Banco Santander, S.A. | 01:09:33 |
| `ESA48010615` | Iberdrola, S.A. | 01:09:34 |
| `ESQ2826000H` | Agencia Estatal de Administración Tributaria (CIF avec lettre de contrôle) | 01:09:35 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `ESA28015866` | contrôle +1 | `InvalidChecksum` | non | non |
| `ESA2801586` | 8 caractères | `InvalidLength` | non | non |
| `ES123456789` | les deux extrémités numériques | `InvalidCharacters` | non | non |
| `ESN01234566` | `N` avec contrôle numérique | `InvalidChecksum` (règle stricte) ou valide (règle permissive) | non | **oui** |

### FI — Finlande

- **Format :** 8 chiffres : le Y-tunnus sans son tiret (`0765432-1` → `FI07654321`, [Vero](https://www.vero.fi/syventavat-vero-ohjeet/ohje-hakusivu/48691/arvonlisaverotus-eu-tavarakaupassa4/)).
- **Algorithme :**
  1. `S = 7·C1 + 9·C2 + 10·C3 + 5·C4 + 8·C5 + 4·C6 + 2·C7`, puis `r = S mod 11`.
  2. Si `r = 0`, `C8 = 0`. Si `r = 1`, le numéro n'est **jamais attribué**, donc invalide. Sinon `C8 = 11 − r`.
  3. Échantillon officiel : `09853608`.
- **Sources :**
  - Décret 288/2001, § 3 ([Finlex](https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2001/288/fin@)), primaire.
  - BMF, page 6.
- **Écarts :** aucun.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `FI01120389` | Nokia Oyj | 01:09:37 |
| `FI19274001` | KONE Oyj | 01:09:38 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `FI01120380` | clé fausse | `InvalidChecksum` | non | non |
| `FI0112038` | 7 chiffres | `InvalidLength` | non | non |

### FR — France

- **Format :** 2 caractères de clé + SIREN à 9 chiffres. VIES : `FRXX 999999999`.
  - Alphabet de la clé : `0123456789ABCDEFGHJKLMNPQRSTUVWXYZ`, sans `I` ni `O`.
- **Algorithme :**
  - **Clé numérique** (les deux caractères sont des chiffres) : `clé = (12 + 3 × (SIREN mod 97)) mod 97`, ce qui équivaut à `(SIREN × 100 + 12) mod 97`. On compare l'entier aux deux chiffres.
  - **Clé alphanumérique** (« anciennes clés » ; au moins un des deux caractères est une lettre) :
    1. `idx(c)` est la position de `c` dans l'alphabet ci-dessus, de 0 à 33.
    2. Si C1 est un chiffre (C2 est alors une lettre) : `s = idx(C1) × 24 + idx(C2) − 10`.
    3. Sinon : `s = idx(C1) × 34 + idx(C2) − 100`.
    4. Valide si `(SIREN + 1 + floor(s / 11)) mod 11 = s mod 11`.
  - **SIREN :** il doit passer **Luhn** (INSEE), **sauf** s'il commence par `000`. C'est le cas des numéros de **Monaco**, observé : `FR73000042183`, SAM MONACO TELECOM, valide dans VIES alors que `000042183` échoue au Luhn.
- **Sources :**
  - La France a refusé la publication (BMF).
  - Luhn du SIREN : INSEE ([xml.insee.fr/schema/siret.html](https://xml.insee.fr/schema/siret.html), § 8), primaire.
  - Formule de la clé numérique : **aucun texte officiel trouvé**. Le BOFiP et la douane ([PDF douane 2021](https://www.douane.gouv.fr/sites/default/files/2021-02/02/VIES_Structure_des_identifiants_TVA_DEB_2021.pdf)) ne donnent que la structure.
  - Clés alphanumériques et exception Monaco : **secondaires seulement**. stdnum et dragonbe concordent sur la clé alphanumérique.
- **Écarts :**
  - dragonbe **ne vérifie pas le Luhn du SIREN** : `FR29123456788` est accepté.
  - dragonbe calcule la clé alphanumérique avec une division flottante (`$checkVal / 11`). Le résultat est correct, mais PHP ≥ 8.1 émet une dépréciation (« Implicit conversion from float… to int loses precision »).
  - stdnum applique le Luhn sauf pour `000`.
- **`FR44732829320` :** clé et Luhn corrects, mais **`valid: false`** dans VIES (01:27:22, après deux `MS_MAX_CONCURRENT_REQ`). Fixture `post-invalid-fr.json`.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `FR59542051180` | SE TOTALENERGIES SE | 01:09:48 (2e essai) |
| `FR27552032534` | SA DANONE | 01:10:04 |
| `FR10632012100` | L'OREAL | 01:10:11 |
| `FR0W314684960` | SEM STE D'ECONOMIE MIXTE DES TRANSPORTS (Semitan, **clé alphanumérique**) | 01:17:14 |
| `FR73000042183` | SAM MONACO TELECOM S.A.M. (**Monaco**, Luhn en échec) | 01:28:25 (2e essai) |

- **Clés alphanumériques :** une seule a été confirmée en direct. `FR1A268600012` et `FR0B196604375` sont bien formés mais `valid: false`. Vecteurs synthétiques de stdnum : `FRK7399859412`, `FR4Z123456782`.

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `FR28552032534` | clé +1 | `InvalidChecksum` | non | non |
| `FR2755203253` | SIREN à 8 chiffres | `InvalidLength` | non | non |
| `FR29123456788` | clé juste, SIREN sans Luhn | `InvalidChecksum` | **oui** | non |
| `FRIO334175221` | lettres `I` et `O` | `InvalidCharacters` | non | non |

### HR — Croatie

- **Format :** 11 chiffres (OIB).
- **Algorithme :** ISO 7064 MOD 11,10 sur C1…C10, avec les mêmes étapes que DE. `C11 = (11 − P) mod 10`.
- **Sources (primaires) :**
  - Zakon o OIB, NN 60/08, art. 3 ([NN](https://narodne-novine.nn.hr/clanci/sluzbeni/2008_05_60_2033.html)).
  - Pravilnik, NN 1/09, art. 3(1) : clé « po međunarodnoj normi ISO 7064 Modul 11,10 » ([NN](https://narodne-novine.nn.hr/clanci/sluzbeni/2009_01_1_6.html)).
  - La Croatie a refusé la publication VIES (BMF), mais la loi suffit.
- **Écarts :** aucun.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `HR81793146560` | Hrvatski Telekom d.d. | 01:10:12 |
| `HR27759560625` | INA, d.d. | 01:10:13 |
| `HR92963223473` | Zagrebačka banka d.d. | 01:10:15 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `HR81793146561` | clé +1 | `InvalidChecksum` | non | non |
| `HR8179314656` | 10 chiffres | `InvalidLength` | non | non |

### HU — Hongrie

- **Format :** 8 chiffres : le « törzsszám » du numéro fiscal `xxxxxxxx-y-zz`.
- **Algorithme (BMF) :**
  1. `A1 = 9·C1 + 7·C2 + 3·C3 + 1·C4 + 9·C5 + 7·C6 + 3·C7`.
  2. `C8 = (10 − A1 mod 10) mod 10`.
  3. Échantillons officiels : `21376414`, `10597190`.
- **Sources :**
  - BMF, page 23.
  - Céginformációs Szolgálat, *Adószám ellenőrzése*, 2018 ([PDF](https://ceginformaciosszolgalat.kormany.hu/download/4/27/02000/adoszam_adoazonosito_ellenorzes_2018.pdf)).
- **Écarts :** aucun.
- **Remarque :** `HU10625790` (MOL) et `HU10537914` (OTP Bank) répondent `valid: false`. **Hypothèse non vérifiée :** ces groupes facturent sous un numéro de groupe TVA (`17…`).

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `HU10773381` | MAGYAR TELEKOM TÁVKÖZLÉSI NYILVÁNOSAN MŰKÖDŐ RÉSZVÉNYTÁRSASÁG | 01:10:18 |
| `HU10484878` | RICHTER GEDEON VEGYÉSZETI GYÁR NYILVÁNOSAN MŰKÖDŐ RT. | 01:10:26 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `HU10773382` | clé +1 | `InvalidChecksum` | non | non |
| `HU1077338` | 7 chiffres | `InvalidLength` | non | non |

### IE — Irlande

- **Format :** VIES : `IE9S99999L IE9999999LL`. Trois versions (BMF) :
  1. **Ancien format :** `C1` chiffre, `C2` lettre `A–Z`, `+` ou `*`, `C3…C7` chiffres, `C8` lettre `A–W`.
  2. **Nouveau format à 8 caractères :** 7 chiffres + lettre `A–W`.
  3. **Nouveau format à 9 caractères :** 7 chiffres + lettre `A–W` + lettre `A–I`.
- **Algorithme :**
  1. **Ancien format :** on le convertit d'abord en `N = 0 C3 C4 C5 C6 C7 C1` (7 chiffres) et on garde C8.
  2. `S = 8·N1 + 7·N2 + 6·N3 + 5·N4 + 4·N5 + 3·N6 + 2·N7`.
  3. Pour le format à 9 caractères : `S += 9 × v(C9)`, avec `A=1, B=2, … I=9`.
  4. `C8 = "WABCDEFGHIJKLMNOPQRSTUV"[S mod 23]`, c'est-à-dire 0 → W, 1 → A … 22 → V.
  5. Échantillons officiels : `8Z49289F`, `3628739L`, `3628739UA`.
- **Sources :**
  - BMF, pages 10 et 11 (primaire).
  - Revenue, *VIES Traders Manual* ([PDF](https://www.revenue.ie/en/tax-professionals/tdm/value-added-tax/vat-information-exchange-system-VIES/vies-traders-manual.pdf)) : « six digits and two letters or seven digits and one or two letters ».
  - Revenue mentionne le « modulus 23 » sans donner les poids.
- **Lettres admises en C9 :** les sources divergent.
  - BMF : `A–I`.
  - stdnum : toute lettre de `WABCDEFGHIJKLMNOPQRSTUV`.
  - jsvat : `A` ou `H` seulement.
  - **dragonbe : n'importe quel caractère**, compté 0 s'il est inconnu. `IE6388047VX` et `IE6388047V0` sont donc acceptés.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `IE6388047V` | GOOGLE IRELAND LIMITED | 01:10:27 |
| `IE8256796U` | MICROSOFT IRELAND OPERATIONS LIMITED | 01:10:28 |
| `IE9692928F` | META PLATFORMS IRELAND LIMITED | 01:10:29 |
| `IE3668997OH` | GOOGLE CLOUD EMEA LIMITED (**9 caractères**) | 01:10:30 |
| `IE8F52100V` | ELECTRICITY SUPPLY BOARD (**ancien format**) | 01:17:32 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `IE6388047W` | lettre de contrôle fausse | `InvalidChecksum` | non | non |
| `IE6388047` | 7 caractères | `InvalidLength` | non | non |
| `IE6388047VX` | C9 hors `A–I` | `InvalidCharacters` | **oui** | non |

### IT — Italie

- **Format :** 11 chiffres :
  - matricule C1…C7, différent de `0000000` ;
  - code du bureau C8…C10, valant 001–100, 120, 121, 888 ou 999 (BMF) ;
  - clé C11.
- **Algorithme (Luhn) :**
  1. `S1 = C1 + C3 + C5 + C7 + C9`.
  2. Pour i pair : `Di = floor(Ci / 5) + (2 × Ci) mod 10`, puis `S2 = D2 + D4 + D6 + D8 + D10`.
  3. `C11 = (10 − (S1 + S2) mod 10) mod 10`.
  4. Échantillon officiel : `00000010215`.
- **Sources (primaires) :**
  - DM du 23 décembre 1976, arts. 8 et 9 ([Gazzetta Ufficiale](https://www.gazzettaufficiale.it/atto/serie_generale/caricaArticolo?art.progressivo=0&art.idArticolo=1&art.versione=1&art.codiceRedazionale=098A2638&art.dataPubblicazioneGazzetta=1998-04-01&art.idGruppo=0&art.idSottoArticolo1=10&art.idSottoArticolo=1&art.flagTipoArticolo=2)).
  - BMF, page 12, pour les codes de bureau.
- **Écarts :**
  - dragonbe ne contrôle pas le code du bureau : `IT12345672005` (bureau 200) est accepté.
  - stdnum applique la même liste que le BMF.
  - jsvat accepte 001–201.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `IT00905811006` | ENI SPA | 01:10:31 |
| `IT00488410010` | TIM S.P.A. | 01:10:33 |
| `IT00881841001` | LEONARDO SOCIETA' PER AZIONI | 01:10:34 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `IT00905811007` | clé +1 | `InvalidChecksum` | non | non |
| `IT0090581100` | 10 chiffres | `InvalidLength` | non | non |
| `IT12345672005` | bureau 200, Luhn juste | Structure | **oui** | non |

### LT — Lituanie

- **Format :** 9 chiffres avec `C8 = 1`, ou 12 chiffres avec `C11 = 1`.
  - Le BMF appelle les numéros à 12 chiffres « temporarily registered taxpayers ».
  - En pratique, de grandes sociétés en ont un (Ignitis grupė).
- **Algorithme (BMF) :**
  1. `corps` = tous les chiffres sauf le dernier.
  2. `S1 = Σ wi × corps[i]`, avec des poids cycliques `1, 2, …, 9, 1, 2` ; `r = S1 mod 11`.
  3. Si `r = 10` : `S2` avec les poids `3, 4, …, 9, 1, 2, 3, 4` ; `r = S2 mod 11`. Si `r = 10` encore, `r = 0`.
  4. La clé (dernier chiffre) doit valoir `r`.
  5. Échantillons officiels : `213179412`, `290061371314`.
- **Source :** BMF, page 24 (primaire).
- **Écarts :** aucun.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `LT230335113` | MAXIMA LT, UAB (adresse renvoyée : `N/A`) | 01:10:35 |
| `LT100004278519` | AB "Ignitis grupė" (**12 chiffres**) | 01:12:46 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `LT230335114` | clé +1 | `InvalidChecksum` | non | non |
| `LT230335123` | `C8 = 2` | Structure | non | non |
| `LT2303351130` | 10 chiffres | `InvalidLength` | non | non |

### LU — Luxembourg

- **Format :** 8 chiffres.
- **Algorithme (BMF) :** `C7C8 = int(C1…C6) mod 89`, sur deux chiffres de 00 à 88. Échantillon officiel : `10000356`.
- **Source :** BMF, page 13 (primaire).
- **Écarts :** aucun.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `LU20260743` | AMAZON EU SARL | 01:10:36 |
| `LU22046007` | PAYPAL (EUROPE) S.A R.L. ET CIE, S.C.A. | 01:10:37 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `LU20260744` | clé +1 | `InvalidChecksum` | non | non |
| `LU2026074` | 7 chiffres | `InvalidLength` | non | non |

### LV — Lettonie

- **Format :** 11 chiffres.
- **Algorithme :**
  - **Personne morale (C1 > 3) :**
    - `S = 9·C1 + 1·C2 + 4·C3 + 8·C4 + 3·C5 + 10·C6 + 2·C7 + 5·C8 + 7·C9 + 6·C10 + 1·C11` ; valide si `S mod 11 = 3`.
    - Autrement dit, `C11 = (3 − S10) mod 11` ; si le résultat vaut 10, le numéro est invalide.
  - **Personne physique (C1 ≤ 3), code personnel :**
    - **Ancien format** `JJMMAA-SNNNC` : la date doit être valide (siècle S : 0 = 1800, 1 = 1900, 2 = 2000) et `C11 = (1 + Σ wi·Ci) mod 11 mod 10`, avec les poids 10,5,8,4,2,1,6,3,7,9.
    - **Nouveau format depuis le 1/7/2017** (commence par `32`) : aucune clé publiée ; les sources se contredisent.
- **Sources :**
  - **Secondaires seulement.** La Lettonie a refusé la publication (BMF).
  - stdnum signale lui-même que l'algorithme personnel n'est « pas confirmé par une source indépendante ».
- **Écarts :**
  - dragonbe **rejette toutes les personnes physiques** (C1 ≤ 3). stdnum les accepte et applique la clé personnelle même aux codes en `32`.
  - jsvat ne contrôle que la date pour les personnes physiques. Pour les personnes morales, il ajoute une règle inexpliquée : si `C1 = 9` et `S10 mod 11 = 4`, retrancher 45.
  - Je n'ai trouvé **aucun numéro réel** dans ce cas parmi 30 organismes publics `9000…` (Wikidata).

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `LV40003032949` | Akciju sabiedrība "Latvenergo" | 01:10:39 |
| `LV40003245752` | Air Baltic Corporation AS | 01:10:40 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `LV40003032940` | clé fausse | `InvalidChecksum` | non | non |
| `LV4000303294` | 10 chiffres | `InvalidLength` | non | non |

Vecteurs personnels synthétiques : `LV01018012347` (ancien format), `LV32123456785` (nouveau format). dragonbe les refuse, stdnum les accepte.

### MT — Malte

- **Format :** 8 chiffres, `C1 ≠ 0`.
- **Algorithme :**
  1. `S = 3·C1 + 4·C2 + 6·C3 + 7·C4 + 8·C5 + 9·C6`.
  2. `C7C8 = 37 − (S mod 37)`, de 01 à 37.
- **Sources :** **secondaires seulement.** Malte a refusé la publication (BMF). Sources : braemoor, jsvat, dragonbe.
- **Écarts :**
  - stdnum vérifie `(3·C1 + … + 9·C6 + 10·C7 + 1·C8) mod 37 = 0`. C'est plus permissif : il accepte aussi `00` et les valeurs +37 ou +74. Exemple : `MT10001700` est accepté par stdnum, refusé par dragonbe.
  - dragonbe exige en plus `C1…C6 > 100000`.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `MT12826209` | GO p.l.c | 01:12:47 |
| `MT15159905` | PricewaterhouseCoopers | 01:13:49 |
| `MT12894031` | THE UNIVERSITY OF MALTA | 01:15:36 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `MT12826200` | clé fausse | `InvalidChecksum` | non | non |
| `MT1282620` | 7 chiffres | `InvalidLength` | non | non |
| `MT01282620` | `C1 = 0` | Structure | non | non |

### NL — Pays-Bas

- **Format :** 12 caractères (VIES : `NLSSSSSSSSSSSS`, où S est une lettre, un chiffre, `+` ou `*`). Depuis le 01/01/2020, deux familles coexistent (BMF) :
  - **Modulo 11** (numéro fondé sur le RSIN) : `^\d{9}B\d{2}$`, avec `C11C12 > 00`.
  - **Modulo 97** (nouveaux numéros des entreprises individuelles, RGPD) : C1…C12 peuvent contenir chiffres, lettres majuscules, `+` et `*` ; `C11C12` vaut de 02 à 98.
    - En pratique, la forme observée reste 9 caractères + `B` + 2 chiffres. Les deux derniers chiffres sont **les chiffres de contrôle ISO 7064**.
- **Algorithme (BMF), dans cet ordre :**
  1. **Modulo 11 :**
     - `A1 = 9·C1 + 8·C2 + 7·C3 + 6·C4 + 5·C5 + 4·C6 + 3·C7 + 2·C8` ; `A2 = A1 mod 11` ;
     - si `A2 = 10`, invalide sous cette règle ; sinon valide si `C9 = A2` et `C11C12 > 00`.
  2. **Seulement si le modulo 11 échoue, modulo 97 :**
     - prendre la chaîne `NL` + les 12 caractères ;
     - remplacer chaque lettre par deux chiffres (`A=10 … Z=35`, `+=36`, `*=37`) ;
     - le grand entier obtenu doit valoir **1 mod 97**.
     - Échantillon officiel : `NL123456789B13` → `23211234567891113`, et `23211234567891113 mod 97 = 1`.
  - Le BMF demande explicitement de tester le modulo 11 d'abord, pour qu'un ancien numéro ne valide pas « par hasard » en modulo 97.
- **Sources :**
  - BMF, pages 14 à 17 (primaire, règles transmises par les Pays-Bas).
  - Belastingdienst : format seul ([page btw-id](https://www.belastingdienst.nl/wps/wcm/connect/nl/btw/content/gebruik-vanaf-1-januari-2020-uw-nieuwe-btw-identificatienummer)).
- **Écarts :**
  - **dragonbe transforme le reste 10 en clé 0** (`($checkVal % 11) > 9 ? 0 : …`), ce qui contredit le BMF : `NL100000060B01` est accepté.
  - stdnum exige 9 chiffres même pour le modulo 97, et accepte « BSN 11-proef **ou** mod 97 ».
- **Vecteurs :**
  - Aucun numéro réel de la famille modulo 97 n'a été vérifié : ce sont des personnes physiques (données personnelles), recherche volontairement écartée.
  - Vecteurs synthétiques : `NL123456789B13` (BMF), `NL001000000B24` (calculé) et `NL002455799B11` (stdnum).

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `NL805734958B01` | BOOKING.COM B.V. (adresse avec `\n` en tête) | 01:10:41 |
| `NL003028112B01` | FISCALE EENHEID ING GROEP N.V., C.S. | 01:12:48 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `NL805734959B01` | C9 +1 | `InvalidChecksum` | non | non |
| `NL805734958B00` | suffixe `00` | Structure | non | non |
| `NL805734958C01` | `C` au lieu de `B` | `InvalidCharacters` | non | non |
| `NL100000060B01` | reste 10 et C9 = 0 | `InvalidChecksum` | **oui** | non |

### PL — Pologne

- **Format :** 10 chiffres.
- **Algorithme (BMF) :**
  1. `R = (6·C1 + 5·C2 + 7·C3 + 2·C4 + 3·C5 + 4·C6 + 5·C7 + 6·C8 + 7·C9) mod 11`.
  2. Si `R = 10`, invalide ; sinon `C10 = R`.
  3. Échantillon officiel : `5260001246`.
- **Source :** BMF, page 27 (primaire). La loi polonaise (Dz.U. 1995 nr 142 poz. 702) ne fixe pas l'algorithme.
- **Écarts :** aucun.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `PL7740001454` | ORLEN SPÓŁKA AKCYJNA | 01:10:46 (2e essai) |
| `PL5250007738` | POWSZECHNA KASA OSZCZĘDNOŚCI BANK POLSKI SPÓŁKA AKCYJNA | 01:10:47 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `PL5250007739` | clé +1 | `InvalidChecksum` | non | non |
| `PL525000773` | 9 chiffres | `InvalidLength` | non | non |

### PT — Portugal

- **Format :** 9 chiffres, `C1 > 0`. Le premier chiffre indique la catégorie : 1–3 personnes, 5 personnes morales, 6 administration…
- **Algorithme (BMF) :**
  1. `R = 11 − (9·C1 + 8·C2 + 7·C3 + 6·C4 + 5·C5 + 4·C6 + 3·C7 + 2·C8) mod 11`.
  2. Si `R = 10` ou `R = 11`, `R = 0`. Valide si `C9 = R`.
  3. Échantillon officiel : `502757191`.
- **Sources :**
  - BMF, page 18 (primaire).
  - DL 14/2013, art. 4 : « os oito primeiros sequenciais e o último um dígito de controlo ».
- **Écarts :** dragonbe ne contrôle pas `C1 > 0` (`PT012345679` accepté) ; stdnum le refuse.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `PT500697256` | EDP, S.A. | 01:10:48 |
| `PT504499777` | GALP ENERGIA SGPS S A | 01:10:50 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `PT500697257` | clé +1 | `InvalidChecksum` | non | non |
| `PT50069725` | 8 chiffres | `InvalidLength` | non | non |
| `PT012345679` | `C1 = 0` | Structure | **oui** | non |

### RO — Roumanie

- **Format :** 2 à 10 chiffres, **sans zéro en tête depuis le 5/12/2007** (BMF). VIES : `RO999999999`, « minimum 2 digits and maximum 10 digits ».
- **Algorithme :**
  1. `corps` = tous les chiffres sauf le dernier, complété à gauche par des zéros jusqu'à 9 chiffres.
  2. `S = 7·b1 + 5·b2 + 3·b3 + 2·b4 + 1·b5 + 7·b6 + 5·b7 + 3·b8 + 2·b9`.
  3. `c = (10 × S) mod 11`, et si `c = 10`, `c = 0`. Valide si le dernier chiffre vaut `c`.
- **Sources :** **secondaires seulement** (ro.wikipedia, stdnum, dragonbe). La Roumanie a refusé la publication (BMF).
- **Écarts :**
  - stdnum (`ro.vat` = `ro.cf`) accepte aussi un CNP à 13 chiffres, absent du format VIES.
  - dragonbe accepte un zéro en tête.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `RO1590082` | OMV PETROM SA | 01:10:56 |
| `RO160796` | AUTOMOBILE-DACIA SA (6 chiffres) | 01:10:57 |
| `RO5022670` | BANCA TRANSILVANIA SA | 01:10:58 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `RO1590083` | clé +1 | `InvalidChecksum` | non | non |
| `RO1` | 1 chiffre | `InvalidLength` | non | non |
| `RO15900820000` | 11 chiffres | `InvalidLength` | non | non |
| `RO015900820` | zéro en tête | Structure | non | non |

### SE — Suède

- **Format :** 12 chiffres = numéro d'organisation (ou personnummer) à 10 chiffres + suffixe à 2 chiffres.
- **Algorithme (BMF) :**
  1. `C11C12` doit valoir **de 01 à 94** selon le BMF. Selon Skatteverket, **toujours 01**.
  2. Luhn sur C1…C10 : `Si = floor(Ci / 5) + (2 × Ci) mod 10` pour i impair ; `R = S1 + S3 + S5 + S7 + S9` ; `C10 = (10 − (R + C2 + C4 + C6 + C8) mod 10) mod 10`.
  3. Échantillon officiel : `556188840401`.
- **Sources :**
  - BMF, page 19.
  - [Skatteverket, page sur les numéros de TVA](https://www.skatteverket.se/foretag/moms/saljavarorochtjanster/forsaljningtillandraeulander/kontrolleramomsregistreringsnummervatnummer/momsregistreringsnummer.4.18e1b10334ebe8bc80002649.html) : « De två sista siffrorna är alltid 01. »
  - SKV 704 (Luhn pour le personnummer).
- **Écarts :**
  - Les deux sources primaires se contredisent sur le suffixe.
  - dragonbe suit le BMF (01–94) ; stdnum suit Skatteverket (01).
  - **Recommandation :** suivre le BMF (règle transmise par la Suède), pour éviter les faux rejets ; VIES tranchera en ligne.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `SE556012579001` | Aktiebolaget Volvo | 01:11:00 |
| `SE556016068001` | Telefonaktiebolaget LM Ericsson | 01:11:01 |
| `SE556042722001` | H & M Hennes & Mauritz AB | 01:11:04 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `SE556012579101` | C10 faux | `InvalidChecksum` | non | non |
| `SE55601257900` | 11 chiffres | `InvalidLength` | non | non |
| `SE556012579002` | suffixe `02` | valide (BMF) ou Structure (Skatteverket) | **oui** | non |

### SI — Slovénie

- **Format :** 8 chiffres ; C1…C7 compris entre 1000000 et 9999999.
- **Algorithme (BMF) :**
  1. `A1 = 8·C1 + 7·C2 + 6·C3 + 5·C4 + 4·C5 + 3·C6 + 2·C7`.
  2. `R = 11 − (A1 mod 11)`. Si `R = 10`, `C8 = 0` ; si `R = 11`, invalide ; sinon `C8 = R`.
  3. Échantillon officiel : `15012557`.
- **Sources :**
  - BMF, page 28.
  - [FURS](https://www.fu.gov.si/davki_in_druge_dajatve/poslovanje_z_nami/vpis_v_davcni_register_in_davcna_stevilka/) : 8 chiffres, contrôle « po modulu 11 ».
- **Écarts :** aucun.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `SI82646716` | KRKA, D.D., NOVO MESTO | 01:11:05 |
| `SI80267432` | PETROL D.D., LJUBLJANA | 01:11:06 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `SI82646717` | clé +1 | `InvalidChecksum` | non | non |
| `SI8264671` | 7 chiffres | `InvalidLength` | non | non |
| `SI02646716` | `C1 = 0` | Structure | non | non |

### SK — Slovaquie

- **Format :** 10 chiffres ; C1 de 1 à 9 ; C3 parmi `2, 3, 4, 7, 8, 9`.
- **Algorithme (BMF) :** le nombre entier doit être divisible par 11. Échantillon valide : `4030000007` ; invalide : `5407062531`.
- **Source :** BMF, page 29 (primaire).
- **Écarts :** stdnum accepte aussi un rodné číslo valide, qui peut avoir un C3 hors liste. dragonbe suit le BMF.

| Numéro valide | Titulaire (VIES) | Heure UTC |
|---|---|---|
| `SK2020273893` | Slovak Telekom, a.s. | 01:11:09 |
| `SK2020317068` | ESET, spol. s r.o. | 01:13:00 |
| `SK2020261353` | Slovenské elektrárne, a.s. | 01:13:02 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `SK2020273894` | non divisible par 11 | `InvalidChecksum` | non | non |
| `SK202027389` | 9 chiffres | `InvalidLength` | non | non |
| `SK2010273893` | `C3 = 1` | Structure | non | non |

### XI — Irlande du Nord

- **Format :** identique à GB, préfixe `XI` (BMF, page 32 ; [GOV.UK](https://www.gov.uk/register-for-vat/selling-or-moving-goods-between-northern-ireland-and-the-eu) : « XI 123456789 instead of GB 123456789 »).
  - **Format 1 :** `GD` + 3 chiffres (ministères, 000–499) ou `HA` + 3 chiffres (autorités de santé, 500–999).
  - **Format 2 :** 9 chiffres, ou 12 chiffres pour les succursales (9 + 3).
- **Algorithme (BMF) :**
  1. `P = int(C1…C7)` ; `S = 8·C1 + 7·C2 + 6·C3 + 5·C4 + 4·C5 + 3·C6 + 2·C7 + int(C8C9)`.
  2. `R1 = S mod 97` (« MOD97 ») ; `R2 = (S + 55) mod 97` (« MOD9755 »).
  3. Valide si l'une des deux conditions est vraie :
     - `R1 = 0` **et** `P` hors de `0100000–0999999`, `9490001–9700000` et `9990001–9999999` ;
     - `R2 = 0` **et** `P` hors de `0000001–1000000`, c'est-à-dire `P > 1000000`.
  4. De plus, `C1…C9 > 000000000`. Pour les succursales, `C10C11C12 > 000`, et seuls les 9 premiers chiffres entrent dans la clé.
  5. `C1C2C3` de `000` à `009` : numéros de l'île de Man.
  6. Échantillon officiel : `434031494`.
- **Sources :**
  - BMF, pages 8, 9, 32 et 33 (primaire).
  - HMRC ne publie pas la formule : [EM3058](https://www.gov.uk/hmrc-internal-manuals/enquiry-manual/em3058) la retient au titre du Freedom of Information Act.
- **Écarts :**
  - dragonbe ignore les plages et accepte une succursale `000` (`XI220430231000`).
  - stdnum accepte un reste 55 quand `C1C2C3 ≥ 100` (`GB100000047`), absent du BMF. Il remplace les plages par un seuil `C1C2C3 ≥ 100` et accepte une forme `GD8888…` à 11 caractères.
  - Exemples de divergence avec le BMF :
    - `GB010000035` : refusé par le BMF, accepté par dragonbe.
    - `GB010000090` : refusé par le BMF, accepté par dragonbe et stdnum.
    - `GB950000087` : refusé par le BMF, accepté par les deux.

| Numéro valide | Titulaire (VIES, préfixe `XI`) | Heure UTC |
|---|---|---|
| `XI220430231` | TESCO PLC | 01:11:10 |
| `XI232128892` | MARKS AND SPENCER P.L.C. | 01:11:11 |
| `XI660454836` | SAINSBURY'S SUPERMARKETS LTD | 01:11:12 |
| `XI245719348` | BRITISH TELECOMMUNICATIONS LIMITED !! BT PLC | 01:11:14 |

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `XI220430232` | clé +1 | `InvalidChecksum` | non | non |
| `XI22043023` | 8 chiffres | `InvalidLength` | non | non |
| `XIGD500` | GD hors 000–499 | Structure | non | non |
| `XIHA499` | HA hors 500–999 | Structure | non | non |
| `XI220430231000` | succursale `000` | Structure | **oui** | **oui** |

### GB — Royaume-Uni (format seul, non couvert par VIES)

- **Format et algorithme :** identiques à XI ; voir ci-dessus.
- **Vecteurs réels :**
  - Le registre officiel est le service HMRC *Check a UK VAT number* ([gov.uk/check-uk-vat-number](https://www.gov.uk/check-uk-vat-number)). Je ne l'ai **pas interrogé**.
    - Le formulaire est interactif.
    - L'API v1 (`api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup/{vrn}`) a été supprimée le 17/02/2025 ; elle a répondu **404 `MATCHING_RESOURCE_NOT_FOUND`**.
    - L'API v2 répond **401 `MISSING_CREDENTIALS`** sans jeton OAuth.
  - L'existence des numéros suivants est donc confirmée **indirectement**, par VIES sous le préfixe `XI` (même numéro HMRC) : `GB220430231` (Tesco PLC), `GB232128892` (Marks and Spencer), `GB660454836` (Sainsbury's Supermarkets), `GB245719348` (British Telecommunications).
  - Une succursale réelle (12 chiffres) ou un numéro GD/HA réel n'ont pas été trouvés. Synthétiques : `GB220430231001`, `GBGD001`, `GBHA599`.

| Numéro invalide | Défaut | Raison attendue | dragonbe | stdnum |
|---|---|---|---|---|
| `GB220430232` | clé +1 | `InvalidChecksum` | non | non |
| `GB22043023` | 8 chiffres | `InvalidLength` | non | non |
| `GBGD500` | GD hors plage | Structure | non | non |
| `GB100000047` | reste 55 | `InvalidChecksum` (BMF) | non | **oui** |

### CH — Suisse (format seul)

- **Format :** `CHE` + 9 chiffres, suivi éventuellement d'un suffixe.
  - Suffixe `MWST`, `TVA` ou `IVA` ([ESTV](https://www.estv.admin.ch/estv/de/home/mehrwertsteuer/uid.html) ; l'abréviation anglaise `VAT` n'est pas admise).
  - stdnum accepte aussi `TPV` (romanche), que l'ESTV ne cite pas.
  - Le préfixe `ADM` désigne des unités administratives et ne sert jamais de numéro TVA.
- **Algorithme (eCH-0097) :**
  1. `S = 5·C1 + 4·C2 + 3·C3 + 2·C4 + 7·C5 + 6·C6 + 5·C7 + 4·C8`, sur les 8 premiers chiffres.
  2. `R = 11 − (S mod 11)`. Si `R = 11`, `C9 = 0`. Si `R = 10`, le numéro **n'est jamais attribué**, donc invalide. Sinon `C9 = R`.
  3. Exemple officiel : `CHE109322551`.
- **Source :** eCH-0097 v5.2.0, § 2.4 ([PDF eCH](https://www.ech.ch/sites/default/files/dosvers/hauptdokument/STAN_d_DEF_2021-07-02_eCH-0097_V5.2.0_Datenstandard%20Unternehmensidentifikation.pdf)), primaire.
- **Écarts :** dragonbe n'a pas de validateur CH. stdnum `ch.uid` suit eCH-0097 ; `ch.vat` exige un suffixe.
- **Vecteurs réels (registre UID, [uid.admin.ch](https://www.uid.admin.ch), consulté le 2026-10-22) :**
  - `CHE-116.281.710 MWST` : « Groupe TVA, Nestlé S.A. », UID actif, registre TVA actif ([fiche](https://www.uid.admin.ch/Detail.aspx?uid_id=CHE-116.281.710)). C'est l'exemple du document de conception.
  - `CHE-116.268.023 MWST` : « MWST-Gruppe Novartis Pharma AG », registre TVA actif ([fiche](https://www.uid.admin.ch/Detail.aspx?uid_id=CHE-116.268.023)).
  - **UID valides mais non inscrits à la TVA** (complément UID `HR`), donc corrects au format mais pas de vrais numéros TVA : `CHE-103.867.266` (Novartis AG), `CHE-101.602.521` (Roche Holding AG).

| Numéro invalide | Défaut | Raison attendue |
|---|---|---|
| `CHE116281711` | clé +1 | `InvalidChecksum` |
| `CHE11628171` | 8 chiffres | `InvalidLength` |

### NO — Norvège (format seul)

- **Format :** numéro d'organisation à 9 chiffres. Une entreprise inscrite au registre de la TVA y ajoute `MVA` (Bokføringsforskriften § 5-1-2, [Lovdata](https://lovdata.no/dokument/SF/forskrift/2004-12-01-1558)).
- **Algorithme :**
  1. `S = 3·C1 + 2·C2 + 7·C3 + 6·C4 + 5·C5 + 4·C6 + 3·C7 + 2·C8`.
  2. `R = 11 − (S mod 11)`. Si `R = 11`, `C9 = 0`. Si `R = 10`, le numéro est invalide. Sinon `C9 = R`.
- **Source :** Brønnøysundregistrene ([brreg.no](https://www.brreg.no/?p=36889)), primaire. La page dit qu'un reste 1 rend le numéro invalide ; le cas « reste 0 → 0 » relève de l'usage et n'est pas écrit.
- **Écarts :** dragonbe n'a pas de validateur NO. stdnum `no.mva` exige le suffixe `MVA`.
- **Vecteurs réels :** API officielle du registre des entités, `https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}`, consultée le 2026-10-22.
  - `NO923609016` : EQUINOR ASA, `registrertIMvaregisteret: true`.
  - `NO984851006` : DNB BANK ASA, `true`.
  - `NO982463718` : TELENOR ASA, `true`.
  - `NO974760673` : REGISTERENHETEN I BRØNNØYSUND, **`false`**. Numéro d'organisation valide, mais pas un numéro TVA. C'est l'exemple du document de conception.

| Numéro invalide | Défaut | Raison attendue |
|---|---|---|
| `NO923609017` | clé +1 | `InvalidChecksum` |
| `NO92360901` | 8 chiffres | `InvalidLength` |

---

## 4. API VIES (REST)

Base : `https://ec.europa.eu/taxation_customs/vies/rest-api`. Contrat OpenAPI officiel (Swagger 2.0) : [swagger_publicVAT.yaml](https://ec.europa.eu/assets/taxud/vow-information/swagger_publicVAT.yaml).

### 4.1 Endpoints

| Méthode et chemin | Dans le contrat officiel | Usage |
|---|---|---|
| `POST /check-vat-number` | oui | Vérifier un numéro (avec ou sans requester) |
| `POST /check-vat-test-service` | oui | Service de test : réponses fixes selon le numéro (voir 4.4) |
| `GET /check-status` | oui | Disponibilité de VIES et de chaque État |
| `GET /ms/{countryCode}/vat/{vatNumber}` | **non** | Endpoint interne de l'interface web ; accepte `?requesterMemberStateCode=…&requesterNumber=…` |

**Corps de `POST /check-vat-number`** (en-tête `Content-Type: application/json` **obligatoire** ; sans lui, HTTP 500 `VOW-ERR-1`) :

| Champ | Type | Obligatoire | Remarque |
|---|---|---|---|
| `countryCode` | string | oui | `EL` et non `GR` (`GR` → `INVALID_INPUT`) ; la casse est corrigée (`lu` → `LU`) |
| `vatNumber` | string | oui | **Sans préfixe pays, sans espace** : un préfixe donne `valid: false`, un espace donne HTTP 400 `VOW-ERR-2600` |
| `requesterMemberStateCode` | string | non | Code du requester ; un code inconnu donne HTTP 400 `VOW-ERR-2500` |
| `requesterNumber` | string | non | Sans préfixe ; s'il est mal formé, `INVALID_REQUESTER_INFO` ; s'il manque alors que le code est présent, HTTP 400 `VOW-ERR-11` |
| `traderName`, `traderStreet`, `traderPostalCode`, `traderCity`, `traderCompanyType` | string | non | Rapprochement approximatif ; hors périmètre du package |

Les noms de champs comptent. stdnum envoie `requesterCountryCode` et `requesterVatNumber`, qui **ne figurent pas au contrat** : VIES les ignore sans erreur et renvoie `requestIdentifier: ""` (observé).

### 4.2 Codes HTTP observés

| HTTP | Cas | Corps |
|---|---|---|
| 200 | Numéro valide ou invalide | `CheckVatResponse` (4.3) |
| **200** | **Erreur d'un État membre ou de VIES** (`MS_MAX_CONCURRENT_REQ`, `INVALID_INPUT`, `INVALID_REQUESTER_INFO`…) | `{"actionSucceed": false, "errorWrappers": [{"error": "…"}]}` |
| 400 | Champ obligatoire manquant (`VOW-ERR-11`), numéro non conforme à la regex de VIES (`VOW-ERR-2600`, ex. espaces), code requester invalide (`VOW-ERR-2500`) | même enveloppe, avec `message` |
| 500 | JSON mal formé ou `Content-Type` absent (`VOW-ERR-1`) | même enveloppe, avec `message` |
| 404 | Chemin inconnu | **HTML** (`text/html`) |
| 405 | Mauvaise méthode (`GET /check-vat-number`) | texte HTML : `Request method &#39;GET&#39; not supported` |

- **Format des réponses :** `Content-Type: application/json` ; JSON indenté avec des espaces avant les deux-points (`"valid" : true`). C'est sans effet pour `json_decode`. `Cache-Control: no-store`.
- **Conséquence pour la conception (4.2 du document) :** avec la règle « réponse non 200 → `HttpStatus` », les erreurs `VOW-ERR-*` deviennent `HttpStatus` et non `RegistryError`. C'est acceptable, puisque notre validation hors ligne les rend improbables. Il faut toutefois lire `errorWrappers` **avant** de regarder `valid` dans une réponse 200.

### 4.3 Formes des réponses

**`POST /check-vat-number`, numéro valide** (`post-valid-be.json`) :

```json
{
  "countryCode" : "BE",
  "vatNumber" : "0417497106",
  "requestDate" : "2026-10-22T01:00:38.289Z",
  "valid" : true,
  "requestIdentifier" : "",
  "name" : "NV Anheuser-Busch InBev",
  "address" : "Grote Markt 1\n1000 Brussel",
  "traderName" : "---",
  "traderStreet" : "---",
  "traderPostalCode" : "---",
  "traderCity" : "---",
  "traderCompanyType" : "---",
  "traderNameMatch" : "NOT_PROCESSED",
  "traderStreetMatch" : "NOT_PROCESSED",
  "traderPostalCodeMatch" : "NOT_PROCESSED",
  "traderCityMatch" : "NOT_PROCESSED",
  "traderCompanyTypeMatch" : "NOT_PROCESSED"
}
```

| Champ | Type | Toujours présent | Remarques |
|---|---|---|---|
| `countryCode` | string | oui | Écho en majuscules |
| `vatNumber` | string | oui | Écho tel qu'envoyé |
| `requestDate` | string | oui | ISO 8601 UTC avec millisecondes et `Z` (`Y-m-d\TH:i:s.v\Z`) ; c'est la source de `checkedAt` |
| `valid` | bool | oui | |
| `requestIdentifier` | string | oui | `""` sans requester ; 16 caractères avec requester (ex. `WAPIAAAAaFhMB-VU`) |
| `name` | string | oui | Nom ; `"---"` si l'État ne le communique pas (DE, ES) ; `""` pour la plupart des invalides |
| `address` | string | oui | Texte multiligne (`\n`) ; voir 4.6 |
| `trader*` | string | oui en production | `"---"` sans rapprochement approximatif ; **absents** dans le service de test |
| `trader*Match` | string | oui en production | `VALID`, `INVALID` ou `NOT_PROCESSED` ; absents dans le service de test |

**Numéro invalide** : même forme, `"valid" : false`.
- Le plus souvent `"name" : ""` et `"address" : ""` (CY, FR, HU…).
- Mais `"---"` pour ES (`post-invalid-es-placeholder-name.json`) et quand VIES rejette le numéro lui-même, comme un préfixe répété (`post-invalid-lu-prefix-repeated-in-vat-number.json`).

**Numéro valide avec requester** (`post-valid-with-requester-dk.json`) : même forme, `"requestIdentifier" : "WAPIAAAAaFhMB-VU"`.
- Le requester utilisé est `BE0417497106` (Anheuser-Busch InBev, société cotée), **choisi seulement pour observer la forme de la réponse**, comme demandé. Je n'ai **pas** utilisé `FR44732829320`.
- Un second essai avec un requester bien formé mais fictif (`IE0000000W`) a aussi reçu un identifiant (`WAPIAAAAaFhMMnNO`). VIES ne contrôle donc pas l'existence du requester. Cette réponse n'a pas été conservée en fixture.

**Erreur** (`post-error-ms-max-concurrent-req-fr.json`, HTTP 200) :

```json
{
  "actionSucceed" : false,
  "errorWrappers" : [ {
    "error" : "MS_MAX_CONCURRENT_REQ"
  } ]
}
```

- `errorWrappers[].message` (string) n'apparaît que pour les erreurs `VOW-ERR-*` (HTTP 400 et 500).
- Le message de `VOW-ERR-2600` contient un gabarit non rempli : `"… regular expression : \"{0}\"."`.

**`GET /ms/{cc}/vat/{n}`** (`get-valid-be.json`) :

```json
{
  "isValid" : true,
  "requestDate" : "2026-10-22T01:00:42.701Z",
  "userError" : "VALID",
  "name" : "NV Anheuser-Busch InBev",
  "address" : "Grote Markt 1\n1000 Brussel",
  "requestIdentifier" : "",
  "originalVatNumber" : "0417497106",
  "vatNumber" : "0417497106",
  "viesApproximate" : {
    "name" : "---", "street" : "---", "postalCode" : "---", "city" : "---", "companyType" : "---",
    "matchName" : 3, "matchStreet" : 3, "matchPostalCode" : 3, "matchCity" : 3, "matchCompanyType" : 3
  }
}
```

- **`userError`** (string) vaut `VALID`, `INVALID`, ou **un code d'erreur** (`MS_MAX_CONCURRENT_REQ`, `INVALID_INPUT`…).
  - Dans ce dernier cas, `isValid` vaut **`false`** et `name` et `address` valent `"---"` (`get-error-ms-max-concurrent-req-fr.json`, `get-error-invalid-input-xx.json`).
- `originalVatNumber` et `vatNumber` peuvent différer quand VIES « corrige » le numéro avant validation (texte `vatResponse_lbl_processing_rule_information` de la FAQ).
- `viesApproximate.match*` est un **entier**, alors que le `POST` utilise des chaînes. Le sens de `3` n'est pas documenté ; il correspond à `NOT_PROCESSED`.

**`GET /check-status`** (`check-status.json`) :

```json
{ "vow" : { "available" : true },
  "countries" : [ { "countryCode" : "AT", "availability" : "Available" }, … ] }
```

- `availability` vaut `Available`, `Unavailable` ou `Monitoring Disabled` (contrat).
- La liste contient les 27 pays + `XI`, avec `EL` pour la Grèce.

### 4.4 Codes d'erreur

Les codes viennent du contrat, des textes de la FAQ (`exceptionError_lbl_*`) et du service de test.

| Code | Sens (FAQ VIES) | Observé en production | Nature |
|---|---|---|---|
| `INVALID_INPUT` | Saisie invalide | oui (`GB`, `GR`, `XX`) | Permanente : erreur de notre côté |
| `INVALID_REQUESTER_INFO` | Numéro du requester invalide | oui (`requesterNumber: "123"`) | Permanente |
| `SERVICE_UNAVAILABLE` | Service indisponible | non (test seulement) | Passagère |
| `MS_UNAVAILABLE` | État membre indisponible | non (test seulement) | Passagère |
| `TIMEOUT` | Délai dépassé côté VIES | non (test seulement) | Passagère |
| `VAT_BLOCKED` | Numéro bloqué | non (test seulement) | Permanente |
| `IP_BLOCKED` | Adresse IP bloquée (usage abusif) | non (test seulement) | Permanente |
| `GLOBAL_MAX_CONCURRENT_REQ` | Trop de requêtes simultanées (global) | non (test seulement) | Passagère |
| `GLOBAL_MAX_CONCURRENT_REQ_TIME` | Idem, sur la tranche horaire | non (test seulement) | Passagère |
| `MS_MAX_CONCURRENT_REQ` | Trop de requêtes simultanées pour cet État | **oui, fréquent** : 15 des 120 tentatives `POST` des lots de vérification (FR 7/15, CZ 5/11, BE 2/10, PL 1/3) ; aussi un `POST` avec requester | Passagère |
| `MS_MAX_CONCURRENT_REQ_TIME` | Idem, sur la tranche horaire | non (test seulement) | Passagère |
| `VOW-ERR-1` | Erreur inattendue (HTTP 500) | oui | Notre requête est mal formée |
| `VOW-ERR-11` | Champ obligatoire manquant (HTTP 400) | oui | Idem |
| `VOW-ERR-2500` | Code requester invalide (HTTP 400) | oui | Idem |
| `VOW-ERR-2600` | Numéro non conforme à la regex (HTTP 400) | oui | Idem |

- `MS_MAX_CONCURRENT_REQ` arrive vite (environ 0,5 s) : VIES refuse sans interroger l'État.
- **Service de test** (`POST /check-vat-test-service`, numéro passé dans `vatNumber`, tout `countryCode`) : `100` → valide (`"name" : "John Doe"`), `200` → invalide, puis :

| Numéro | Code |
|---|---|
| `201` | `INVALID_INPUT` |
| `202` | `INVALID_REQUESTER_INFO` |
| `300` | `SERVICE_UNAVAILABLE` |
| `301` | `MS_UNAVAILABLE` |
| `302` | `TIMEOUT` |
| `400` | `VAT_BLOCKED` |
| `401` | `IP_BLOCKED` |
| `500` | `GLOBAL_MAX_CONCURRENT_REQ` |
| `501` | `GLOBAL_MAX_CONCURRENT_REQ_TIME` |
| `600` | `MS_MAX_CONCURRENT_REQ` |
| `601` | `MS_MAX_CONCURRENT_REQ_TIME` |

  - Toutes ces réponses arrivent en HTTP 200 ; elles sont enregistrées.
  - Les réponses du service de test n'ont **pas** les champs `trader*`. Un parseur ne doit donc pas les exiger.

### 4.5 Le piège du `GET`, et l'endpoint recommandé

- **Observation du 2026-10-21, confirmée le 2026-10-22 :**
  - `GET /ms/FR/vat/44732829320` → `"isValid" : false`, `"userError" : "MS_MAX_CONCURRENT_REQ"` (fixture `get-error-ms-max-concurrent-req-fr.json`). Idem pour CZ.
  - `GET /ms/XX/vat/…` → `"isValid" : false`, `"userError" : "INVALID_INPUT"`.
  - Un client qui lit seulement `isValid` conclurait à tort à `NotFound`.
- **Comparaison directe** : sept numéros, un `POST` puis un `GET` à 1,2 s d'intervalle.

| Numéro | POST | GET |
|---|---|---|
| `FR10632012100` | `MS_MAX_CONCURRENT_REQ` (0,5 s) | `isValid false` + `MS_MAX_CONCURRENT_REQ` |
| `FR59542051180` | valide (7,6 s) | valide (7,6 s) |
| `FR27552032534` | `MS_MAX_CONCURRENT_REQ` | `isValid false` + `MS_MAX_CONCURRENT_REQ` |
| `BE0403170701` | valide (4,2 s) | valide (3,4 s) |
| `BE0403199702` | valide (3,3 s) | valide (3,4 s) |
| `CZ00177041` | valide (10,5 s) | valide (9,7 s) |
| `CZ60193336` | `MS_MAX_CONCURRENT_REQ` | valide (10,8 s) |

  - Les deux endpoints passent par les mêmes files d'attente des États : la disponibilité et la latence sont comparables. Le seul `GET` réussi après un `POST` refusé relève du hasard du moment.
- **Recommandation : `POST /check-vat-number`.**
  1. Il est au contrat officiel ; le `GET` n'est pas documenté et peut changer sans préavis.
  2. Une erreur y est **structurellement distincte** d'une réponse « invalide » (`actionSucceed` et `errorWrappers` au lieu de `valid`).
  3. Il porte le requester dans le corps, au lieu de la query string.
- **Règle de décodage proposée :**
  1. HTTP ≠ 200 → `HttpStatus`.
  2. Corps qui n'est pas du JSON → `InvalidJson`.
  3. `errorWrappers` présent → `RegistryError`, avec `registryErrorCode = errorWrappers[0].error`.
  4. `valid` absent ou d'un autre type → `Schema`.
  5. `valid === true` → `Found` ; `valid === false` → `NotFound`.
- **Si un jour le `GET` est utilisé :** toute valeur de `userError` autre que `VALID` ou `INVALID` est une erreur, quel que soit `isValid`.

### 4.6 Autres points utiles à l'implémentation

- **Latence :**
  - de 0,4 à **11,8 s** pour une réponse valide (DK 11,8 s mesuré par `curl` ; CZ 10,5 à 10,8 s ; FR 7,6 s) ;
  - environ 0,5 s pour un refus `MS_MAX_CONCURRENT_REQ`.
  - Un `timeout` de 10 s couperait une partie des réponses valides. **Recommandation : 30 s par défaut.**
- **Normalisation de `name` et `address`** (valeurs observées) :
  - **Retours à la ligne :**
    - `"Grote Markt 1\n1000 Brussel"` ;
    - `"Novo Alle 1\n2880 Bagsværd\n"` (fin de ligne finale, DK, IT) ;
    - `"\nOOSTERDOKSKADE 00163\n1011DL AMSTERDAM\n"` (NL, MT : en tête) ;
    - `"78\n\nMILL\nSTREET …"` (MT : ligne vide).
  - **Espaces :**
    - `"ΛΕΩΦΟΡΟΣ ΚΗΦΙΣΙΑΣ 99        15124 - ΜΑΡΟΥΣΙ"` (EL : suite d'espaces) ;
    - `"MUNICIPIUL  BUCUREŞTI, … Nr. 22 "` (RO : double espace, espace final).
  - **Marqueurs d'absence :** `"---"` (DE, ES, erreurs `GET`), `""` (invalides) et `"N/A"` (adresse LT).
    - Proposition : traiter `---`, la chaîne vide et `N/A` comme `null`. `N/A` est une décision à valider : c'est une valeur littérale de l'État.
  - **Séparateurs dans les noms :** `||` (EL) et ` !! ` (BT, XI). À conserver tels quels : c'est du texte brut.
  - **Groupe TVA CZ :** nom générique et adresse sous forme d'URL. À conserver tel quel.
- **Disponibilité planifiée** (FAQ VIES, `help_txt_XXavailability`) :

| État | Indisponibilité planifiée |
|---|---|
| DE | Tous les jours de 23:00 à 01:30 |
| ES | Vers 06:30 quelques minutes |
| IT | Le lundi à partir de 06:00, 30 à 60 min |
| LU | Le vendredi vers 19:30, environ 30 min |
| MT | Le mardi de 07:00 à 07:30, et le 3e lundi de 05:00 à 05:30 |
| PT | Le lundi vers 07:30, 30 à 60 min |
| RO | Du samedi 21:50 au dimanche 21:50, presque chaque week-end |
| GB / XI | Le samedi de 07:30 à 10:30, et presque chaque jour de 04:30 à 04:40 |

  - Le fuseau de ces heures n'est pas précisé (probablement CET).
  - DE a pourtant répondu le 2026-10-22 vers 01:08 UTC (03:08 heure de Paris).
- **Abus :** la FAQ prévient que l'IP d'origine est bloquée en cas d'usage abusif (`IP_BLOCKED`). Aucun nombre de requêtes autorisé n'est publié.

### 4.7 Fixtures enregistrées (`tests/Fixtures/vies/`)

Toutes sont les octets bruts du corps de la réponse, sans retouche. 66 fichiers au total.

| Fichier | HTTP | Contenu |
|---|---|---|
| `check-status.json` | 200 | `GET /check-status`, tout disponible |
| `post-valid-{at,be,bg,cy,cz,dk,ee,el,es,fi,fr,hr,hu,ie,it,lt,lu,lv,mt,nl,pl,pt,ro,se,si,sk,xi}.json` | 200 | Une réponse valide par pays : nom, adresse et marqueurs variés (27 fichiers ; DE ci-dessous) |
| `post-valid-de-without-name-address.json` | 200 | DE valide, `name` et `address` à `---` |
| `post-valid-cz-vat-group.json` | 200 | Groupe TVA tchèque (`699004742`) |
| `post-valid-fr-alphanumeric-key.json` | 200 | `FR0W314684960`, clé alphanumérique |
| `post-valid-fr-monaco.json` | 200 | `FR73000042183`, Monaco (SIREN sans Luhn) |
| `post-valid-ie-old-format.json` | 200 | `IE8F52100V`, ancien format |
| `post-valid-with-requester-dk.json` | 200 | Avec requester : `requestIdentifier` rempli |
| `post-invalid-cy.json` | 200 | Invalide, `name` et `address` à `""` |
| `post-invalid-fr.json` | 200 | `FR44732829320` invalide |
| `post-invalid-es-placeholder-name.json` | 200 | Invalide, `name` et `address` à `---` |
| `post-invalid-lu-prefix-repeated-in-vat-number.json` | 200 | `vatNumber: "LU20260743"` → `valid: false` (piège du préfixe) |
| `post-error-ms-max-concurrent-req-fr.json` | 200 | `MS_MAX_CONCURRENT_REQ` |
| `post-error-invalid-input-gb.json` | 200 | `INVALID_INPUT` (`countryCode: "GB"` ; identique pour `GR`) |
| `post-error-invalid-requester-info.json` | 200 | `INVALID_REQUESTER_INFO` |
| `post-http400-vow-err-11-missing-field.json` | 400 | `VOW-ERR-11` (`vatNumber` vide) |
| `post-http400-vow-err-2500-invalid-requester-ms.json` | 400 | `VOW-ERR-2500` (`requesterMemberStateCode: "XX"`) |
| `post-http400-vow-err-2600-vat-number-regex.json` | 400 | `VOW-ERR-2600` (espace dans le numéro) |
| `post-http500-vow-err-1-malformed-json.json` | 500 | `VOW-ERR-1` (JSON tronqué ; même corps sans `Content-Type`) |
| `post-test-service-valid.json`, `post-test-service-invalid.json` | 200 | Service de test, `100` et `200` |
| `post-test-service-error-*.json` (11 fichiers) | 200 | Chaque code du service de test (4.4) |
| `get-valid-be.json` | 200 | `GET` valide |
| `get-valid-with-requester-dk.json` | 200 | `GET` avec requester |
| `get-invalid-be.json` | 200 | `GET` invalide (`userError: "INVALID"`, `name: ""`) |
| `get-error-ms-max-concurrent-req-fr.json` | 200 | **Le piège** : `isValid: false` + `MS_MAX_CONCURRENT_REQ` |
| `get-error-ms-max-concurrent-req-cz.json` | 200 | Même piège, CZ |
| `get-error-invalid-input-xx.json` | 200 | `isValid: false` + `INVALID_INPUT` |
| `http404-not-found.html` | 404 | Corps HTML (pour le cas `InvalidJson`) — ce n'est pas du JSON |
| `get-http405-method-not-allowed.html` | 405 | Corps texte/HTML — ce n'est pas du JSON |

Les réponses intermédiaires de même forme (autres `MS_MAX_CONCURRENT_REQ`, autres numéros valides) restent dans le répertoire de travail de la session ; elles n'ont pas été ajoutées.

---

## 5. Points incertains et décisions à prendre

1. **Raison d'échec des règles de structure.**
   - `FailureReason` couvre les caractères, la longueur et la clé. Il ne couvre pas les règles suivantes :
     - premier chiffre interdit (BE, CZ, DE, DK, MT, PT, SI) ;
     - `10` imposé (EE) ;
     - 8e ou 11e chiffre égal à `1` (LT) ;
     - code de bureau (IT) ;
     - suffixe `00` (NL) ;
     - plages GD/HA et succursale `000` (GB/XI) ;
     - préfixe `12` (CY).
   - **Proposition :** les ranger sous `InvalidChecksum`, puisqu'elles relèvent de la règle de validité et non de la forme. Autre option : ajouter un cas, par exemple `InvalidStructure`. À trancher.
2. **Sources secondaires seulement.** Pour BG (sauf EGN), CY (lettre de contrôle), CZ (IČO et numéros en `6`), EL, ES (CIF), FR (formule de clé, clés alphanumériques, Monaco), LV, MT et RO, aucun texte officiel ne publie l'algorithme. Les règles retenues sont celles sur lesquelles dragonbe, stdnum et braemoor concordent, avec les écarts signalés.
3. **Règles officielles contradictoires ou plus strictes que les bibliothèques :**
   - **SE :** suffixe 01–94 (BMF) ou 01 (Skatteverket). Proposition : BMF.
   - **IE :** C9 `A–I` (BMF), toute lettre (stdnum) ou `A`/`H` (jsvat). Proposition : BMF.
   - **GB/XI :** plages du BMF, que ni dragonbe ni stdnum n'appliquent. Proposition : BMF.
   - **NL :** reste 10 invalide (BMF ; dragonbe le transforme en 0). Le modulo 97 admet des lettres, `+` et `*` (BMF), alors que stdnum exige 9 chiffres.
   - **EE :** `10` imposé (BMF), ignoré par dragonbe et stdnum.
   - Le croisement prévu en 7. du document (« comparer nos résultats à `dragonbe/vies` ») doit donc **lister ces écarts attendus**, sinon les tests échoueront.
4. **CY, premier chiffre.** Les nouveaux TIC en `6` depuis 2023 sont **non vérifiés** : l'avis du Département des impôts n'a pas pu être ouvert. L'exclusion de `12` n'a pas de source.
5. **ES, chiffre ou lettre de contrôle du CIF selon l'entité :** pas de source primaire. Proposition : rester permissif (stdnum).
6. **MT : `37 − r`** (dragonbe, jsvat) ou congruence mod 37 (stdnum, plus large). Proposition : stricte. Je n'ai vu aucun numéro réel en `00` ni supérieur à 37.
7. **LV, personnes physiques :** clé des anciens codes personnels « non confirmée » selon stdnum. Aucune règle publiée pour les codes en `32` (depuis 2017). La règle jsvat « C1 = 9, retrancher 45 » reste inexpliquée.
8. **BE et EL, saisies courtes :** compléter ou non les anciens numéros à 9 chiffres (BE) et à 8 chiffres (EL). VIES documente le complément pour BE (note 3) ; pour EL, seul stdnum le fait.
9. **Vecteurs réels manquants :**
   - FR à clé alphanumérique : un seul confirmé.
   - NL modulo 97, BG à 10 chiffres, LV et CZ de personnes physiques : écartés pour ne pas manipuler de données personnelles.
   - GB succursale et GD/HA : non trouvés.
   - GB : confirmé seulement via VIES `XI`, faute d'accès au registre HMRC.
10. **Identité des titulaires DE et ES :** VIES ne renvoie pas le nom. L'attribution vient des mentions légales (Siemens, Deutsche Telekom) ou de la notoriété du CIF (Telefónica, Santander, Iberdrola, AEAT). Volkswagen n'a pas été revérifié.
11. **HU :** l'hypothèse « groupe TVA » pour MOL et OTP (`valid: false`) n'est pas vérifiée.
12. **`requestIdentifier` :** VIES l'émet pour un requester fictif bien formé. Il ne prouve donc que la consultation, pas l'identité du demandeur. À mentionner dans la documentation du package.
13. **Exemples du document de conception à corriger :**
    - `FR44732829320` est invalide dans VIES : ne pas le présenter comme `Found` ni comme `requester`. Utiliser par exemple `FR27552032534` (Danone) ou `FR10632012100` (L'Oréal).
    - `NO974760673` n'est pas inscrit à la TVA : il reste correct comme exemple de **format**.
    - `CHE116281710`, `EL094014201` et `BE0403170701` sont réels et valides.
