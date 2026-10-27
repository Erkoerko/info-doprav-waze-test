# Info doprav – rozšírenie Bratislava, návrh 27.10.2026

**NIE JE NASADENÉ.** Verejný Telegram, pravidelné spúšťače a publikovanie ostávajú vypnuté. Rozpočet 0 €.

## Schválená zmena prahu
Pri porovnateľnej trase len kandidát pri **najmenej +5 min a súčasne +30 %**, potvrdený v **dvoch** meraniach. Vyššia premávka nedokazuje nehodu. Referencia Waze bez real-time nie je automaticky obvyklá hodnota na danú hodinu.

## Pokrytie
- Pôvodné: **8 smerových trás** Stupava/Pezinok/Senec/Šamorín ↔ okraj Bratislavy.
- 4 okrajové profily ↔ centre: **8 smerových trás**, manuálny skript `waze_city_links_pilot.py`, cieľový centrálny bod na Palisádach je skúšobný (zo skoršieho testu).
- 5 cestných mostov: **10 smerových trás**. Na začiatok Most SNP, Apollo, Prístavný (6), potom Lafranconi a Lužný (4). Starý most nie pre bežnú autodopravu.
- Mestské ťahy: **8 dvojíc = 16 smerových trás**. Prvá etapa Račianska, Vajnorská, Galvaniho, Dunajské nábrežie (8); druhá Trnavská cesta, Bajkalská, Gagarinova–Prievozská, Einsteinova (8).

Plný návrh: **42 smerových trás**. Bez presných bodov pre mosty a mestské úseky nepridávať živé merania. Pri krátkom úseku mosta zaradiť aj príjazd, aby zdržanie nebolo mimo meraného úseku. Vymeniť príliš krátke body za vhodné prejazdové profily až po kontrolách.

## Limity kapacity
Doterajších 8 trás: konzervatívne 448 požiadaviek pracovný deň.
Nové trasy: návrh 22 meraní v pracovný deň (30 min v špičkách; 60 min inde).
Etapa 1: 30 smerov = 448 + 22 × 22 = **932 pokusov/pracovný deň**.
Plný rozsah: 42 smerov = 448 + 34 × 22 = **1196 pokusov/pracovný deň**.
Pri projektovom strope 1000 pokusov/deň by plná frekvencia nestačila. Pred zapnutím skrátiť rozsah alebo merania. Strop nepreukazuje kvótu Waze. Počítanie musí zahŕňať aj chybové pokusy. GitHub Actions public standard runners sú bezplatné, no plánované spustenia môžu meškať.

## Prevádzková bezpečnosť
1. Časy z dvoch bodov bez úplného map-matching sú len **kandidáti**.
2. Zmena nazvov cesty alebo dĺžky o > 5 % → zadržať čas, nie vyslať falošné upozornenie.
3. Pre nové mestské úseky zaznamenať referenčné dĺžky až po súkromnom schválení prvého mapového testu.
4. Koncové body centra voľné pre smerové príjazdy; otestovať legálny prístup v oboch smeroch.
5. Rovnaký incident môže zasiahnuť viac meraných úsekov. Zlučovať upozornenia, žiadne násobné správy pre tú istú udalosť.
6. Nikdy nevyvodzovať sprejazdnenie z výpadku zdroja.
7. Telegram nedostáva správy z manuálnych GitHub pilotov.

Zdroj plánovania mestských ťahov: hlavné cestné okruhy a radiály Bratislavy (ZÁKOS). Precízne umiestnenie meracích bodov podlieha mapovému overeniu. `config/bratislava_expansion_proposal.json` je plán, nie produkčný register.

## Výsledok manuálneho testu centra 27.10.2026 o 09:48 Europe/Bratislava

Všetkých **8/8 nových smerov** vrátilo odpoveď. Nula smerov je produkčne overená a nula správ bola publikovaná.
Prvé varianty: Lamač→centrum 16,7 min (bez live 9,3; +7,4), centrum→Lamač 10,0 min;
Rača→centrum 19,4, opačne 13,7; D1/Galvaniho→centrum 14,7, opačne 10,0;
R7/Nivy→centrum 8,6, opačne 7,2 min.

- Lamač→centrum: prvá alternatíva Pražská/Štefánikova, jediné meranie prekročilo nový prah +5 min a +30 %. **Nie je to potvrdené upozornenie**.
- Centrum→Lamač: najrýchlejší variant ide cez **Most SNP, Petržalku, Lafranconi a Sitinu** (12,45 km), alternatíva cez Brniansku má 8,06 km. Ide o zjavne rozdielne vedenia; preto čas nepopisovať ako pevný úsek Pražskej.
- Rača→centrum: najrýchlejší variant využíva vedľajšie komunikácie Pekná cesta/Horská/Malokrasňanská pred Račianskym mýtom. Neprezentovať ho ako nemenné meranie celej Račianskej.
- D1/Galvaniho a R7/Nivy smer centrum: najrýchlejšie varianty môžu využiť Prístavný most a Most SNP. Ten istý problém môže ovplyvniť viac meraní; neskôr spojiť duplicity.

### Aktualizovaná testovacia kontrola

Manuálny `waze_city_links_pilot.py` vypíše najrýchlejší **neobmedzený** variant, jeho vlastný non-live referenčný čas a zdržanie, identifikáciu významných ciest a kontrolný odtlačok zo zoznamu ulíc. Začal používať schválený prah **+5 min a +30 %** len na diagnostiku kandidátov; na publikovanie stále nemá oprávnenie.
Nové offline testy skúšajú odlišné mosty, poradie alternatív, HOV filtrovanie a rozhodnutie o prahu. Odtlačok cesty nie je jej geometrické overenie. Pri zmene identifikácie trasy medzi meraniami sa porovnanie musí prerušiť a posúdiť.

Následný krok: schváliť smerovo prístupný centrálny bod a referenčné dĺžky každého smeru; až potom zvážiť pilotný zber do Google Sheets. Mosty a mestské ťahy zostávajú kandidátmi bez potvrdených GPS bodov. Plánovač stále vypnutý.

## Test mostov 27.10.2026 o 10:17 (manuálny, 6/6)

Skutočné merania vozovky mostov zo skúšky GitHub Actions:

| Most | sever → juh | juh → sever |
|---|---:|---:|
| SNP | 0,3 min, 0,34 km | 0,3 min, 0,29 km |
| Apollo | 0,3 min, 0,38 km | 0,7 min, 0,71 km |
| Prístavný | 0,7 min, 0,67 km | 0,5 min, 0,69 km |

Waze na všetkých šiestich úsekoch pomenoval skutočný most. **Časy sú krátke preto, že sa meria iba mostná vozovka; kolóny pred mostom v meraní chýbajú.** To nezakladá použiteľné upozornenie o doprave. Trasy zostávajú neoverené pre produkčné monitorovanie.

### Rozpracovanie merania príjazdov (skúšobné, nie nasadené)

Samostatný skript `scripts/waze_bridge_approaches_pilot.py` používa šesť mostných smerov z úspešného testu ako východisko. Získava reálne uzly príjazdových ciest z OpenStreetMap a predbežne vyberá body asi 0,65–1,7 km za každou stranou mosta, ideálne 1,1 km. Používa tieto predbežné cesty:
- SNP: Staromestská / Panónska cesta
- Apollo: Košická / Dolnozemská alebo Einsteinova
- Prístavný: D1 na oboch stranách

Pri nejednoznačnej polohe nevymýšľa body; príslušný smer zostane bez Waze požiadavky. Odpoveď Waze musí pomenovať požadovaný most, nepoužívať druhý zo sledovaných mostov, a mať dĺžku najviac 9 km. **Názov mosta a približná dĺžka nie sú úplným geografickým overením.** Údaje sú výlučne pre ručnú diagnostiku a neskoršiu kontrolu meracích bodov.

Spustenie manuálneho testu: `.github/workflows/waze-bridge-approaches.yml`. Rozvrh a Telegram zostávajú vypnuté, nulový rozpočet zostáva podmienkou.

## Test rozšírených nájazdov 27.10.2026 o 10:28 – zistená chyba

Všetkých šesť smerov vrátilo Waze odpoveď. **Predbežne prijateľných je iba 5/6**, všetky naďalej potrebujú kontrolu; verejná prevádzka: 0.

| Most | Sever → juh | Juh → sever | Diagnostika |
|---|---|---|---|
| SNP | 4,0 min / 3,40 km | 5,1 min / 2,92 km | Rámcovo správny most; severný dojazd v jednom smere ide aj cez Hodžovo a Palisády – skontrolovať |
| Apollo | 4,3 min / 2,62 km | 4,5 min / 2,95 km | Predbežne použiteľné; ďalšie alternatívy cez Prístavný most odmietnuté |
| Prístavný | **9,8 min / 13,46 km – NEPLATNÉ** | 1,6 min / 2,70 km | Sever→juh robí obchádzku cez D2 a Bratskú; južný bod je pravdepodobne na nevhodnej vozovke |

Pôvodný výber uzla kontroloval iba blízkosť a smer polohy vzhľadom na most. Nekontroloval, ktorým **smerom je povolené po konkrétnej OSM vozovke jazdiť**. Rovnaký južný bod Prístavného mosta bol preto použitý pre oba protismerné testy.

### Oprava po teste

Manuálny pilot teraz:
- Pri Moste SNP a Prístavnom moste vyžaduje súlad orientácie jednosmernej vozovky podľa OSM s požadovaným smerom jazdy; keď správny bod nenájde, nezadáva fiktívne meranie.
- Označuje dlhé obchádzky ako neplatné podľa pomeru trasy ku vzdušnej vzdialenosti (maximum 2,2-násobok) a podľa rozdielu (maximum +2,2 km); základný maximálny limit 9 km zostáva záložnou kontrolou. Ide o ochranné heuristiky, nie dôkaz exaktnej geometrie.
- Nepriraďuje ani overenému názvu mosta stav aktívneho dopravného upozornenia.
- Rozšírené offline regresné testy overujú pozorovanú chybnú 13,46 km obchádzku, správne smerovanie jednosmerných OSM úsekov a prijatie pôvodnej 2,70 km varianty v opačnom smere.

Opravený program ešte **nebol opakovane vykonaný**. Súkromné merania, zber do Sheets, rozvrh a publikovanie zostávajú vypnuté.

## Oprava výpadku Overpass 27.10.2026 o 10:51

Manuálny GitHub beh `40483909138` skončil **HTTP 502 Bad Gateway** pri prvom požiadavku na `overpass-api.de`. **Waze nebolo volané**. Pôvodný test výberu bodov na základe smeru jednosmerných vozoviek sa teda v tomto behu vôbec neuskutočnil. Offline testy kroku "Offline testy vyberu prijazdov" prešli.

Modul `waze_bridge_approaches_pilot.py` preto teraz:
- Vykoná **maximálne dva** mapové odbery: po jednom z verejných bezplatných inštancií `overpass-api.de` a `overpass.private.coffee`.
- Pri HTTP 502/503, sieťovej chybe, neplatnom JSON alebo prázdnej odpovedi skúsi druhú inštanciu.
- Limit 25 s na server, 8 MB odpoveď, žiadne opakované volanie preťaženej inštancie, nulové poplatky.
- Ak obe inštancie zlyhajú, zámerne skončí chybou **bez akejkoľvek Waze požiadavky** a bez aktualizácie údajov; zlyhanie nie je signálom sprejazdnenia.
- Nové offline regresné testy obsahujú chybu 502 + úspešnú zálohu, dva súčasné výpadky a neplatnú odpoveď.

Táto oprava je uložená, ale na reálnom GitHub runneri **ešte nebola opakovane otestovaná**. Ďalší test ponecháva pravidelné zberanie aj Telegram vypnuté. Verejné Overpass inštancie nemajú garantovanú dostupnosť; po schválení meracích bodov ich chceme ukladať do stáleho registra a neodoberatť mapovú geometriu pri každom dopravnom meraní.
