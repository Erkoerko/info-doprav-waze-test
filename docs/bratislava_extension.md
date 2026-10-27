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
