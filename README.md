# Urenregistratie Moneybird

Een Streamlit-app voor het registreren van gewerkte uren in Moneybird met een gebruiksvriendelijke preview en bevestigingsstap.

## Functionaliteit

- Selecteer contact, project, tijdsperiode en werkdagen.
- Automatische voorvertoning met feestdagenfilter.
- Definitief inboeken na bevestiging.

## Starten met Docker

1. Zorg dat je een `secrets.toml` bestand klaar hebt met je Moneybird API-gegevens (of vul ze via de UI in).
2. Build en start de container:

```bash
docker build -t urenregistratie .
docker run -p 8501:8501 -v $(pwd)/.streamlit:/app/.streamlit urenregistratie
```

Ga naar [http://localhost:8501](http://localhost:8501) om de app te openen.

## Moneybird configuratie

Plaats het volgende in `.streamlit/secrets.toml`:

```toml
[moneybird]
token     = "<jouw-token>"
admin_id  = "<jouw-administratie-id>"
user_id   = "<jouw-user-id>"
```

### 🔐 API-token genereren

1. Log in op [moneybird.com](https://moneybird.com).
2. Ga naar **Mijn profiel** via je gebruikersmenu rechtsboven.
3. Klik op **Connect** > **Nieuw API-token genereren**.
4. Geef het token een naam, selecteer de administratie(s), en klik op **Aanmaken**.
5. Kopieer en bewaar het token veilig (je ziet het maar één keer).

### 🧾 Administratie-ID vinden

1. Ga in Moneybird naar je administratie (bedrijfsnaam bovenin).
2. De administratie-ID staat in de URL, bijvoorbeeld:

```
https://moneybird.com/440747403501372858/timesheet
                        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                       dit is je admin_id
```

### 👤 User-ID vinden

1. Ga naar **Instellingen > Gebruikers**.
2. Klik op je naam om de gebruikerspagina te openen.
3. In de URL zie je je user-ID, bijvoorbeeld:

```
https://moneybird.com/440747403501372858/users/440747342302283468
                                             ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                            dit is je user_id
```

## GitHub Container Registry

Een GitHub Actions workflow bouwt en pusht automatisch een image naar `ghcr.io` bij elke wijziging in de `main`-branch:

```text
ghcr.io/<github-gebruiker>/urenregistratie_moneybird:latest
```

## Vereisten

De app gebruikt deze Python-packages:

```text
streamlit
requests
holidays
python-dateutil
```
