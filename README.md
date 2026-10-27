# Info doprav — Waze pilot (dva body)

**Stav k 27. 10. 2026: TEST ONLY.** Z GitHubu sa neposiela nic do Telegramu,
neukladaju sa pravidelne data a neexistuje automaticky spustac.

## Aktualny zjednoduseny postup

Pre kazdy zo styroch koridorov v oboch smeroch sa pouzije IBA zaciatocny
a konecny GPS bod z povodneho registra. Priebezne kontrolne body sa pri
merani nevyzaduju.

Test zavola Waze cez pywaze, overi, ci nazvy ciest patria do
pozadovaneho koridoru, a porovna dlzku s prvym testovanym vysledkom
(maximalna odchylka 5 %). Toto je zakladna poistka proti presmerovaniu,
**nie plne geometricke overenie**. Vysledky sa mozu mylit, ak sa Waze
presmeruje v ramci podobnej dlzky.

Pri platnej trase sa vypisu:
- aktualny odhad casu jazdy (minuty);
- odhad bez zivych dopravnych dat z Waze (nie nevyhnutne hodinovy priemer);
- cas jazdy v podmienkach free-flow;
- rozdiel v minutach a percentach.

Pilot vypise `threshold_candidate=True`, ked je rozdiel **aspon 10 minut
a zaroven 30 %**. Na realny alert budu potrebne dve po sebe iduce
porovnatelne merania. To nie je dokaz nehody ani prekazky, iba
vacsieho zdrzania.

## Ako spustit

1. Otvor **Actions**.
2. Vyber **Waze – dva body, osem smerov (manualny test)**.
3. Klikni **Run workflow**.
4. Otvor kroky **Overit pravidla bez internetu** a
   **Zmerat osem smerov podla dvoch bodov**.

Workflow: [.github/workflows/waze-endpoints.yml](.github/workflows/waze-endpoints.yml).
Skript: [scripts/waze_endpoint_pilot.py](scripts/waze_endpoint_pilot.py).

## Co zostava vypnute

- ziadne pravidelne volania Waze;
- ziadny zapis do Google Sheets;
- ziadne automaticke verejne ani sukromne Telegram spravy;
- ziadne platené API, karta ani predplatne.

Existujuce starsie testy geometrie zostavaju v repozitari ako diagnostika;
nie su nutnou podmienkou noveho dvojbodoveho pilotu.
