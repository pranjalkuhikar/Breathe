# Deliberate Technical Tradeoffs

To deliver a production-ready, high-fidelity prototype within a concise development window, we made three deliberate technical exclusions. These tradeoffs prioritize code maintainability, speed, and clean separation of concerns.

---

## 1. Linear Billing Cycle Prorating
- **What we did NOT build**: We did not implement an engine that splits a utility bill across calendar months (e.g. allocating 18 days of energy usage to November and 12 days to December). Instead, we map the entire bill's consumption to the `billing_end_date`.
- **Why**: 
  - Prorating assumes linear, identical consumption for every day of a billing cycle. In reality, utility consumption is highly non-linear, heavily influenced by weather changes (cooling/heating spikes) and plant operational shifts.
  - Linear proration adds massive database queries (writing fractional records and tracking calendar months allocations) which makes auditing highly complex for carbon auditors who prefer inspecting exact, matching utility bills. Mapping to the end date is standard practice for early-stage ESG disclosure platforms and remains clean and transparent.

---

## 2. Dynamic GIS / OpenStreetMap / Google Maps API Integration
- **What we did NOT build**: We did not implement dynamic external coordinate lookups for flights and hotel stays. Instead, we seeded a local `AirportLookup` database of key international flight hubs.
- **Why**: 
  - Ingesting thousands of travel logs while calling external HTTP APIs (like Google Geocoding or OpenStreetMap) introduces extreme network latency, rate-limiting failures, potential cost overruns, and security/privacy concerns (sending client travel logs to public APIs).
  - Seeded local databases are extremely fast, fully deterministic, completely offline, and maintain strict data privacy compliance.

---

## 3. Full OAuth2 / Active Directory Tenant Authentication
- **What we did NOT build**: We did not build dynamic user signup flows, OAuth logins, or tenant invitations. Instead, we seeded a default admin user and a standard multi-tenant database schema where all tables point to an `Organization` record.
- **Why**:
  - Setting up enterprise identity management (SSO, dynamic JWT tokens, dynamic invites) requires significant boilerplate code and configuration, adding friction for the evaluator trying to run the app locally.
  - We proved the exact architectural layout of multi-tenancy (by segregating all tables via `Organization` FKs and preparing active row-level queries) while keeping local setup as simple as a single shell command.
