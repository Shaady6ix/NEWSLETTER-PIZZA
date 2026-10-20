PIZZA Newsletter

> [!NOTE]
> **Aktualizacja — 20.10.2026:** Pizzera wyłączyła promocje. Będę aktualizował co jakiś czas repo, stay tuned


Pizza XXL za 37 zł? Spoko opcja

<a href="https://buycoffee.to/fuzler" target="_blank">
  <img src="https://img.shields.io/badge/Postaw%20mi%20kaw%C4%99-FUZLER-ffdd00?logo=buy-me-a-coffee&amp;logoColor=000000"
       alt="Postaw mi kawę" width="220" />
</a>

<img width="514" height="209" alt="Domino’s Newsletter"
     src="https://github.com/user-attachments/assets/4d7a3f95-a836-4ce8-bfa9-1ac7e1e0af7c" />

> [!IMPORTANT]
> Projekt ma charakter edukacyjny i służy do nauki automatyzacji przeglądarki oraz testowania formularzy. Nie jest powiązany z Do*****s Pizza ani przez nią wspierany.

> [!WARNING]
> Korzystaj wyłącznie z własnego adresu e-mail, zgodnie z aktualnym regulaminem promocji i zasadami serwisu. Nie używaj narzędzia do obchodzenia limitów, masowego tworzenia zgłoszeń, nadużyć promocyjnych ani przetwarzania cudzych danych.

<a href="https://buycoffee.to/fuzler" target="_blank">
  <img src="https://img.shields.io/badge/Postaw%20mi%20kaw%C4%99-FUZLER-ffdd00?logo=buy-me-a-coffee&amp;logoColor=000000"
       alt="Postaw mi kawę" width="220" />
</a>


## O projekcie

Generator kodów 50% żniżki. Chcesz pizze za pół darmo? Dobrze trafiłeś

> [!NOTE]
> Dostępność, warunki i wartość rabatów zależą od bieżącej oferty D******s. Projekt nie gwarantuje otrzymania kodu ani możliwości jego wykorzystania.


## Wymagania

- Pizzeria D*****s w okolicy
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
