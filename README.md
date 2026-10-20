# Domino’s Newsletter

Pizza XXL za 37 zł? Spoko opcja

<a href="https://buycoffee.to/fuzler" target="_blank">
  <img src="https://img.shields.io/badge/Postaw%20mi%20kaw%C4%99-FUZLER-ffdd00?logo=buy-me-a-coffee&amp;logoColor=000000"
       alt="Postaw mi kawę" width="220" />
</a>

<img width="514" height="209" alt="Domino’s Newsletter"
     src="https://github.com/user-attachments/assets/4d7a3f95-a836-4ce8-bfa9-1ac7e1e0af7c" />

<a href="https://buycoffee.to/fuzler" target="_blank">
  <img src="https://img.shields.io/badge/Postaw%20mi%20kaw%C4%99-FUZLER-ffdd00?logo=buy-me-a-coffee&amp;logoColor=000000"
       alt="Postaw mi kawę" width="220" />
</a>


## O projekcie

Generator kodów 50% żniżki. Chcesz pizze za pół darmo? Dobrze trafiłeś


## Wymagania

- Pizzeria Domino's w okolicy
- Głód
- Python 3.12 lub nowszy
- połączenie z internetem

## Instalacja

Uruchom PowerShell/CMD w katalogu projektu:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m camoufox fetch
```

## Użycie

Sprawdzenie strony i selektorów bez wysyłania formularza:

```powershell
.\.venv\Scripts\python.exe run1.py --check
```

Jeden kod:

```powershell
.\.venv\Scripts\python.exe run1.py --live
```

Kilka kodów (np. 5):

```powershell
.\.venv\Scripts\python.exe run1.py --count 5
```

## Wyniki 

- `--preview` nie uruchamia przeglądarki.
- `--count x` generuje kod x ilość razy 
- `--live` generuje jeden kod 
- Raporty w `runs/` i plik `kody.csv` mogą zawierać adresy e-mail, treść wiadomości i kody.

## Pliki

- `run.py` — skrypt QA i kolorowy baner CMD.
- `requirements.txt` — zależności Pythona.
- `podglad-cmd.txt` — przykładowe komunikaty tekstowe.

