# Resolved Ambiguities and Key Product Decisions

When ingesting real-world ESG activity logs, data format compliance is almost non-existent. Below is a log of resolved ambiguities, custom algorithms, and questions we would pose to the Product Manager.

---

## 1. SAP Fuel: German Column Headers and obtrusive keys
- **Ambiguity**: SAP column headers can be German, standard abbreviations, or completely custom. Plant codes (e.g., `DE01`) mean nothing without mappings.
- **Resolution**:
  - We implemented a robust fuzzy header-matching service. `WERKS` (or `werk`, `plant`), `MATNR` (or `material`, `item`), `MENGE` (or `menge`, `quantity`, `qty`), `MEINS` (or `einheit`, `unit`), and `BUDAT` (or `date`, `posting_date`) are automatically aligned.
  - If a plant code is not found in the seeded `PlantLookup` table, instead of failing, the row is successfully ingested with the name `"Unknown SAP Plant (code)"`, but marked as `FLAGGED` with a warning so the analyst can map it or adjust the Friendly Name in-place.
- **PM Question**: *Should we support a UI configuration panel where analysts can register custom column headers or create plant lookup records on the fly?*

---

## 2. Utility Electricity: Non-aligned Billing Cycles
- **Ambiguity**: Electricity portal exports usually represent billing cycles (e.g. November 12 to December 14) rather than clean calendar months, and might be in `kWh` or `MWh`.
- **Resolution**:
  - We normalize `MWh` directly to `kWh` (multiply by 1000).
  - We store the billing `start_date` and `end_date` on the Activity Record, using the `end_date` as the standard transaction date.
  - We flag billing periods longer than 45 days as suspicious, representing missed utility cycles.
- **PM Question**: *Would the carbon modeling team prefer that we prorate/distribute consumption across calendar months (e.g., allocating 18 days of usage to November and 14 days to December)?*

---

## 3. Corporate Travel: Flights without Distances
- **Ambiguity**: Platforms like Concur provide flights with departure and arrival airport codes (e.g. `JFK-LAX`) rather than distances, and different categories represent different cabin tiers or hotel nights.
- **Resolution**:
  - We seeded a spatial database of major airports (`AirportLookup`). If departure and arrival are present, we dynamically calculate the **Great-Circle Distance** in kilometers using the mathematical **Haversine formula**.
  - We automatically apply DEFRA/GHG Protocol flight categories: if a flight is shorter than 500 km (short-haul), economy is 0.15 kg/km, business 0.22 kg/km. If it is long-haul (>=500 km), economy is 0.10 kg/km, business 0.29 kg/km.
  - Ground mileage is normalized to km, and hotel stays use night factors. If an IATA airport code is missing from our spatial index, the row is ingested, but flagged as suspicious with a fallback distance (e.g., 1000 km).
- **PM Question**: *Should we build an integration with a third-party airport distance API to handle obscure or private airport runways?*

---

## 4. Parser Dialect Autodetection
- **Ambiguity**: European SAP exports frequently use semicolons (`;`) instead of commas (`,`) as delimiters, causing generic CSV parsers to crash.
- **Resolution**:
  - We implemented a dialect sniffer in our Django views that samples the first 1KB of the file. If semicolons predominate, it automatically switches the parser delimiter to `;`, handling German CSV exports flawlessly.
