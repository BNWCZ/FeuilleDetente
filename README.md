# Feuille Détente

Automatisation de la saisie de la feuille des temps hebdomadaire sur le portail
PeopleSoft de votre entreprise, via [Playwright](https://playwright.dev/python/).

Le script se connecte, crée (ou rouvre) la feuille des temps de la semaine,
saisit les heures, remplit les informations additionnelles et
enregistre un **brouillon**.

> ⚠️ Outil non officiel, fourni « tel quel ». Vérifiez toujours la feuille avant
> de vous y fier, et respectez les politiques internes de votre entreprise.

## Ce que fait l'outil

- Connexion PeopleSoft puis navigation vers « Mes Déclarations heures ».
- Création d'une feuille de temps pour le samedi de la semaine (ou réouverture
  si elle existe déjà).
- Saisie de **8 h par jour ouvré** sur la ligne **Avant-vente (intercontrat)**.
- Les **week-ends** et les **jours fériés nationaux français** sont
  automatiquement laissés à 0 h (jours fériés calculés, Pâques incluse).
- Remplissage des informations additionnelles France (repos quotidien +
  localisation matin/après-midi : Bureau / Télétravail / N/A).
- Enregistrement du brouillon.
- Capture d'écran de chaque étape dans `debug/`.

## Limites importantes (à lire avant usage)

1. **Ligne intercontrat uniquement.** Toutes les heures sont saisies sur la
   ligne « Avant-vente ». Les lignes de temps projet (code projet / activité) ne
   sont **pas** gérées. L'outil ne convient donc qu'aux personnes **sans
   affectation projet** (intercontrat).
2. **Congés / RTT / absences manuels.** Tout jour de
   semaine que vous ne déclarez pas via `--conges` est saisi comme travaillé
   (8 h). Pensez à les passer explicitement (voir ci-dessous).
3. **Télétravail manuel.** Les jours de télétravail doivent être indiqués via
   `--tt`. Les jours non listés sont considérés comme des jours de
   présence au bureau.
4. **Jours fériés nationaux seulement.** Les fériés régionaux (ex. Alsace-Moselle)
   ne sont pas pris en compte.
5. **Brouillon uniquement.** Le script enregistre un brouillon ; il ne soumet
   **pas** la feuille pour approbation.

## Prérequis

- Python 3.10+
- Playwright et le navigateur Chromium

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copiez le modèle `.env.example` en `.env` et renseignez vos identifiants
PeopleSoft :

```bash
cp .env.example .env
```

```ini
UID=prenom.nom
PASSWORD=votre_mot_de_passe
LOGIN_URL=https://votre-portail-peoplesoft.exemple.com/psp/<site>/?cmd=login&languageCd=CFR
```

`LOGIN_URL` est l'adresse de connexion du portail PeopleSoft (demandez-la à
votre équipe si vous ne la connaissez pas). Le fichier `.env` est ignoré par git
et ne doit jamais être committé.

## Utilisation

```bash
python main.py [options]
```

| Option        | Description                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| `--tt`        | Jours de télétravail, séparés par des virgules (ex. `lundi,mercredi`).      |
| `--conges`    | Jours de congé / absence, séparés par des virgules (ex. `vendredi`).        |
| `--samedi`    | Date du samedi cible au format `JJ/MM/AAAA` (défaut : samedi de la semaine courante). |
| `--headless`  | Lance le navigateur en arrière-plan (sans fenêtre).                         |
| `--dry-run`   | Affiche le résumé prévu **sans** rien saisir.                               |

Les noms de jours sont en minuscules et en français : `lundi`, `mardi`,
`mercredi`, `jeudi`, `vendredi`.

### Exemples

```bash
# Aperçu de la semaine courante, sans rien saisir
python main.py --dry-run

# Télétravail lundi et vendredi
python main.py --tt lundi,vendredi

# Congé le vendredi, télétravail le mercredi
python main.py --conges vendredi --tt mercredi

# Cibler une semaine précise (samedi de fin de période)
python main.py --samedi 18/10/2025 --dry-run
```

## Comment gérer fériés, congés et télétravail

- **Jours fériés nationaux** : automatiques, rien à faire (laissés à 0 h).
- **Congés / RTT / absences** : à déclarer avec `--conges jeudi,vendredi`.
  Sinon ils seront saisis comme travaillés (8 h).
- **Télétravail** : à déclarer avec `--tt lundi,mardi`. Les jours ouvrés non
  listés sont comptés « Bureau ».
- **Toujours commencer par `--dry-run`** pour vérifier le résumé (total
  d'heures, Bureau/TT, fériés) avant la saisie réelle.

## Débogage

Chaque étape produit une capture d'écran dans `debug/`. En mode non-headless, le
navigateur reste ouvert à la fin pour inspection (Ctrl+C pour quitter).

## Structure du projet

| Fichier                  | Rôle                                                              |
| ------------------------ | ----------------------------------------------------------------- |
| `main.py`                | Point d'entrée CLI + logique de construction des jours.           |
| `week.py`                | Calcul de la semaine (dimanche→samedi) et des jours fériés.       |
| `automation.py`          | Automatisation du navigateur (Playwright).                        |

## Maintenance

Projet offert à la communauté, sans mainteneur attitré. N'hésitez pas à forker,
pousser vos améliorations et vous organiser entre vous : il n'y a pas de
processus de revue imposé. L'outil est fourni « tel quel », sans garantie.
