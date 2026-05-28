# SOURCES.md — Source Research

---

## 1. SAP Fuel & Procurement Data

**What I researched:**
SAP transaction MB51 (Material Document List) is the standard way to extract material movements. ME2M extracts purchase orders by material. I read SAP's official help documentation for both transactions, and looked at real export examples shared in SAP community forums and GitHub repos that process SAP exports.

**What I learned:**
- SAP exports are not standardised. The column headers depend on the client's language setting (German in many European/global deployments, English elsewhere).
- Quantities use the locale's decimal separator — German SAP uses `1.234,56` for 1234.56.
- Dates come as `DD.MM.YYYY` in German locale, `YYYYMMDD` in some programmatic exports.
- Plant codes (`Werk`) are 4-character codes that mean nothing without the client's plant master table. `1000` is the default first plant in many German SAP installations.
- Movement type 261 = goods issue to production order (most common fuel consumption trigger). 201 = goods issue to cost centre.
- SAP DOES include reversal documents in the same export (type 262 reverses 261). If you sum everything without filtering reversals, you double-count.
- Material groups are client-configurable. There's no global standard for "this material group = fuel."

**What my sample data looks like and why:**
The sample CSV (`MB51_fuel_2024.csv`) uses German column names (`Buchungsdatum`, `Kurztext`, `Menge`, `ME`, `Werk`, `Warengruppe`, `Bewegungsart`, `MBlNr`) because that's the format I most commonly see referenced in real SAP implementations. Quantities are in litres (`L`) for diesel and petrol, and `KG` for LPG/CNG. One row uses `GAL` (gallons)  facilities in some regions use imperial. One row has a quantity >50,000 L to test the suspicious flag. Document numbers follow the SAP convention of 10-digit material document numbers (49xxxxxxxx range).

**What would break in a real deployment:**
1. The material group filter is hardcoded. Every client has different material group assignments.
2. Plant lookup is a 4-entry hardcoded dict. Real clients have 10-200+ plants.
3. We don't handle service entry sheets (transaction ML81N)  some companies record fuel as services, not material movements.
4. SAP can export in XLSX instead of CSV. We'd need to add an XLSX reader.

---

## 2. Utility / Electricity Data

**What I researched:**
I looked at portal export formats from BESCOM (Bengaluru), MSEDCL (Maharashtra), and Tata Power online portals, and also the US Green Button Data / ESPI standard (XML and CSV variants). I also read HCMI and GHG Protocol guidance on Scope 2 electricity accounting.

**What I learned:**
- Indian utility portals typically export consumer number, billing period (start/end date), units consumed in kWh, tariff category, and bill amount in INR. Some also include peak/off-peak splits.
- Billing periods are NOT calendar months. BESCOM bills every ~60 days for domestic consumers, monthly for industrial. The billing period start depends on when the meter reader visited.
- Some older meters report in kVAh (kilovolt-ampere-hours) instead of kWh. The conversion requires the power factor, which is not always in the export.
- India's grid emission factor is published annually by the Central Electricity Authority (CEA). The 2023 value is 0.716 kg CO2e / kWh (national weighted average). State-specific factors exist but require knowing which DISCOM supplies the facility.
- The GHG Protocol allows either location-based or market-based Scope 2 accounting. Market-based requires Renewable Energy Certificates (RECs) data. We do location-based only.

**What my sample data looks like and why:**
Four meters for four facilities, three months of data (Jan–Mar 2024). Consumption figures are plausible for industrial/commercial facilities: 185,000 kWh/month for a plant, 42,000 kWh for a warehouse, 21,000 kWh for an office. One row has a billing period that overlaps another (to test duplicate detection). One row has units in MWh with an absurd value (to test the >1,000,000 kWh flag).

**What would break in a real deployment:**
1. We use the national average grid EF. A Scope 2 audit might require state-specific or market-based factors.
2. kVAh → kWh conversion without power factor is a guess. We flag it but don't refuse.
3. PDF bills (the most common format small facilities have) are not handled at all.
4. Multi-currency bill amounts — we store them but don't convert.

---

## 3. Corporate Travel Data

**What I researched:**
I read SAP Concur's Travel & Expense Report Extract documentation (the standard CSV extract format from Concur Reporting). I also looked at Navan's (formerly TripActions) export format documentation and the GHG Protocol Scope 3 Standard guidance on Category 6 (Business Travel). For emission factors I used DEFRA's 2023 greenhouse gas conversion factors (the spreadsheet Annex 6, Transport section).

**What I learned:**
- Concur exports trip-level data: one row per expense claim. A round-trip flight is usually one row with total distance, not two rows.
- Distance is NOT always provided. Many Concur implementations don't capture it. You get origin/destination city or airport code and have to compute it yourself.
- Cabin class IS usually captured (it's required for corporate booking tools). It matters a lot for emissions: business class is ~3x economy per km due to seat area allocation.
- Hotel stays don't have a mileage. The standard methodology (HCMI) gives ~20 kg CO2e per room-night for a global average.
- Ground transport (taxis, car rentals) often has no distance. You might get only a cost.
- DEFRA includes a Radiative Forcing Index (RFI) uplift of 1.891 for flights to account for non-CO2 effects at altitude. This is debated but DEFRA includes it in their recommended methodology.
- Navan's format uses "trip_date" instead of Concur's "Travel Date", and "traveller_name" instead of "Employee". Our alias system handles both.

**What my sample data looks like and why:**
14 rows covering flights (domestic and international), hotels, and ground transport. Employees are Indian names with realistic routes (BOM-DEL, DEL-LHR, BOM-SIN). One row has a taxi with no distance to test the cost-based fallback. Flight distances match real airport pairs using the haversine formula against actual airport coordinates.

**What would break in a real deployment:**
1. Our airport code dictionary covers 17 airports. A real client might have flights to 200+ airports.
2. We don't handle multi-segment itineraries (connecting flights as separate rows in some systems).
3. Car mileage claims (employees driving personal cars) use a single EF. In reality it depends on car type reported.
4. Currency conversion for international hotel costs isn't handled — we just ignore the amount for hotels and use nights × EF.
