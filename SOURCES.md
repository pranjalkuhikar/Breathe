# Research on Data Sources and Glitches

A core part of this assignment is researching what these three data sources look like in the real world and designing parser systems that handle their typical glitches.

---

## 1. SAP Fuel & Procurement Data
- **Real-World Shape**: SAP tables (e.g. `MSEG`, `EKPO`) are historically queried via custom ABAP reports or OData service extracts, resulting in flat text files (CSV, TSV, or semi-colon delimited).
- **What We Learned**:
  - Column headers are often standard German SAP database keys: `WERKS` (Plant/Factory), `MATNR` (Material), `MENGE` (Quantity), `MEINS` (Base Unit of Measure), and `BUDAT` (Posting Date).
  - Volumetric units are highly inconsistent: `L`, `LIT`, `LITRES`, `GAL`, `USG`, or `M3`.
  - Date formats are often native SAP strings like `YYYYMMDD` (e.g., `20260515`) or European formats like `DD.MM.YYYY`.
- **What Our Sample Data Simulates**:
  - Semi-colon delimited rows, German headers, multiple dates variations, and mixed units mapping. It also includes a negative quantity row (to simulate return adjustments) and an exceptionally large row (to simulate data-entry error outliers).
- **What Would Break in Production**: 
  - If a company introduces completely custom material names (e.g., "Premium Clean Eco-Fuel"), our keyword matching service (`diesel` or `gas`) would fail, mapping it to `"Unknown SAP Material"`. We would need a robust material-to-fuel mapping table in the admin panel.

---

## 2. Utility Electricity Data
- **Real-World Shape**: Facilities teams usually download billing reports from portal extracts. 
- **What We Learned**:
  - Billing cycles are highly off-calendar, matching utility read cycles.
  - Meter readings use different energy units (`kWh` vs `MWh`).
  - Grid emission factors differ enormously by region (e.g., carbon-intensive coal grids vs clean hydro grids).
- **What Our Sample Data Simulates**:
  - Custom facility names (e.g. Frankfurt Manufacturing Hub), dates crossing calendar months, standard units, and a massive spike.
- **What Would Break in Production**:
  - Utility bill formats frequently change, especially when companies transition to green tariffs (e.g., solar credits or renewable energy certificates). A production system needs to handle negative grid values (solar exports) and track clean vs dirty electricity line items.

---

## 3. Corporate Travel (Flights, Hotels, Ground)
- **Real-World Shape**: Travel logs are exported as bulk CSV/JSON files from Concur or Navan API outputs.
- **What We Learned**:
  - Travel portals rarely calculate exact flight mileage, instead exposing departure and arrival airport codes (e.g., `JFK` and `LAX`).
  - Flight emission factors are non-linear: takeoffs represent a huge percentage of fuel burn. Therefore, short-haul flights (< 500 km) actually have a higher carbon intensity per kilometer than long-haul flights.
  - Cabin class (Economy vs Business) has a massive impact: business class seats take up more physical space on a plane, so they are allocated a larger share of the flight's total carbon emissions.
- **What Our Sample Data Simulates**:
  - Flight legs with IATA codes, cabin classes (Economy vs Business), hotel nights, rental car mileage, and an unknown airport segment (testing fallbacks).
- **What Would Break in Production**:
  - Multi-city flight bookings (e.g. `JFK-LHR-DEL-SIN`) are often exported as a single booking line with comma-separated IATA segments. A production parser would need to split these segments, compute intermediate legs, and handle layovers.
