"""Content library for the demo dataset.

Everything here is data: the fictional vendor, reps, companies, people, and the scene fragments
that demo.py assembles into calls, meetings, emails and notes. Templates are plain str.format_map
templates; demo.py builds the context dictionary (names, numbers, dates) once per deal and per
interaction. Keep fragments specific (numbers, names, dates, objections) so the judge has real
sentences to quote. No em dashes anywhere in this file.

Layout:
  1. Vendor, reps, companies, industries, name pools, titles
  2. Rep questions per behaviour tag, buyer statements per element and level
  3. Small talk, agendas, pitch, logistics, objections, interruptions, closings
  4. Emails, notes, meeting summaries, unlinked meeting topics
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Vendor, reps, companies
# ---------------------------------------------------------------------------

VENDOR = {
    "name": "Northwind Analytics",
    "domain": "northwind-analytics.example",
    "product": "Northwind",
    "modules": ["Northwind Core", "Northwind Boards", "Northwind Finance"],
}

COMPETITOR = "Lumen BI"
CONSULTANCY = "Harbour Data"

# profile: (before training, after training). Levels: high, medium, low.
# gaps: elements the rep never asks about; rare: elements the rep asks about roughly one time in ten.
REPS = [
    {"name": "Amira Khan", "email": "amira.khan@northwind-analytics.example", "before": "high", "after": "high", "gaps": [], "rare": []},
    {"name": "Tom Ellis", "email": "tom.ellis@northwind-analytics.example", "before": "low", "after": "high", "gaps": [], "rare": []},
    {"name": "Jonas Weber", "email": "jonas.weber@northwind-analytics.example", "before": "low", "after": "low", "gaps": [], "rare": []},
    {"name": "Sofia Marin", "email": "sofia.marin@northwind-analytics.example", "before": "medium", "after": "medium", "gaps": ["PP"], "rare": ["CH"]},
]

# Per-industry numbers. Ranges are (low, high); demo.py draws one value per deal so a story stays
# consistent across its interactions. money values are in thousands of the deal currency.
INDUSTRIES = {
    "logistics": {"kpi": "on-time-in-full", "report": "the weekly OTIF pack", "cost_driver": "expedited freight and penalty credits",
                  "pct": (83, 89), "pct_target": (93, 96), "n_days": (7, 12), "n_target": (3, 5), "money1": (110, 260), "money2": (18, 45),
                  "n_hours": (14, 30), "n_people": (2, 4), "system": "Sage 200"},
    "manufacturing": {"kpi": "quoted margin accuracy", "report": "the monthly margin report", "cost_driver": "mispriced quotes and overtime",
                      "pct": (78, 86), "pct_target": (92, 95), "n_days": (9, 14), "n_target": (4, 6), "money1": (140, 320), "money2": (25, 60),
                      "n_hours": (16, 32), "n_people": (2, 5), "system": "SAP Business One"},
    "retail": {"kpi": "stock accuracy", "report": "the Monday trading report", "cost_driver": "markdowns and stock-outs",
               "pct": (86, 91), "pct_target": (96, 98), "n_days": (6, 10), "n_target": (2, 4), "money1": (120, 280), "money2": (20, 50),
               "n_hours": (12, 26), "n_people": (2, 4), "system": "Dynamics 365"},
    "wholesale": {"kpi": "order fill rate", "report": "the weekly fill-rate report", "cost_driver": "back-orders and emergency purchasing",
                  "pct": (84, 90), "pct_target": (95, 97), "n_days": (7, 11), "n_target": (3, 5), "money1": (100, 240), "money2": (15, 40),
                  "n_hours": (12, 28), "n_people": (2, 4), "system": "NetSuite"},
    "healthcare": {"kpi": "agency staffing spend", "report": "the monthly staffing pack", "cost_driver": "agency shifts booked blind",
                   "pct": (14, 19), "pct_target": (8, 10), "n_days": (10, 16), "n_target": (4, 6), "money1": (180, 420), "money2": (30, 70),
                   "n_hours": (18, 34), "n_people": (2, 4), "system": "Sage Intacct"},
    "hospitality": {"kpi": "forecast occupancy accuracy", "report": "the weekly revenue pack", "cost_driver": "over-staffed shifts and unsold rooms",
                    "pct": (80, 87), "pct_target": (93, 95), "n_days": (6, 11), "n_target": (2, 4), "money1": (90, 220), "money2": (15, 40),
                    "n_hours": (12, 24), "n_people": (2, 3), "system": "Xero"},
    "energy": {"kpi": "customer churn", "report": "the monthly retention report", "cost_driver": "late win-back offers",
               "pct": (13, 17), "pct_target": (8, 10), "n_days": (8, 13), "n_target": (3, 5), "money1": (150, 380), "money2": (25, 65),
               "n_hours": (16, 30), "n_people": (2, 4), "system": "Dynamics 365"},
    "insurance": {"kpi": "claims cycle time", "report": "the monthly claims pack", "cost_driver": "leakage on slow claims",
                  "pct": (68, 76), "pct_target": (88, 92), "n_days": (9, 14), "n_target": (4, 6), "money1": (160, 400), "money2": (30, 70),
                  "n_hours": (18, 32), "n_people": (3, 5), "system": "NetSuite"},
    "construction": {"kpi": "WIP reporting accuracy", "report": "the monthly WIP report", "cost_driver": "unbilled work and cash tied up",
                     "pct": (72, 80), "pct_target": (90, 94), "n_days": (12, 18), "n_target": (5, 7), "money1": (200, 450), "money2": (35, 80),
                     "n_hours": (20, 36), "n_people": (2, 4), "system": "Sage 200"},
    "education": {"kpi": "budget variance reporting", "report": "the termly finance pack", "cost_driver": "unplanned supply cover",
                  "pct": (74, 82), "pct_target": (90, 94), "n_days": (12, 20), "n_target": (5, 8), "money1": (60, 150), "money2": (10, 30),
                  "n_hours": (10, 22), "n_people": (2, 3), "system": "Sage Intacct"},
    "services": {"kpi": "billable utilisation", "report": "the monthly utilisation report", "cost_driver": "unbilled hours and late invoices",
                 "pct": (66, 73), "pct_target": (78, 82), "n_days": (8, 12), "n_target": (3, 5), "money1": (120, 300), "money2": (20, 55),
                 "n_hours": (12, 26), "n_people": (2, 4), "system": "Xero"},
}

# 32 fictional mid-market companies. region: UK or EU (drives currency, hosting region and name pools).
COMPANIES = [
    {"name": "Brightwater Logistics", "domain": "brightwater-logistics.example", "region": "UK", "country": "United Kingdom", "city": "Leeds", "industry": "logistics", "units": "depots", "n_units": 14},
    {"name": "Fenwick Foods", "domain": "fenwickfoods.example", "region": "UK", "country": "United Kingdom", "city": "Newcastle", "industry": "manufacturing", "units": "production lines", "n_units": 9},
    {"name": "Marlow Insurance Group", "domain": "marlowinsurance.example", "region": "UK", "country": "United Kingdom", "city": "Bristol", "industry": "insurance", "units": "claims teams", "n_units": 6},
    {"name": "Kestrel Energy Retail", "domain": "kestrelenergy.example", "region": "UK", "country": "United Kingdom", "city": "Glasgow", "industry": "energy", "units": "regions", "n_units": 5},
    {"name": "Oakhurst Care Homes", "domain": "oakhurstcare.example", "region": "UK", "country": "United Kingdom", "city": "Birmingham", "industry": "healthcare", "units": "homes", "n_units": 23},
    {"name": "Tidewell Pharmacies", "domain": "tidewell.example", "region": "UK", "country": "United Kingdom", "city": "Cardiff", "industry": "retail", "units": "branches", "n_units": 41},
    {"name": "Stanmore Building Supplies", "domain": "stanmorebs.example", "region": "UK", "country": "United Kingdom", "city": "Reading", "industry": "wholesale", "units": "branches", "n_units": 18},
    {"name": "Pennine Textiles", "domain": "penninetextiles.example", "region": "UK", "country": "United Kingdom", "city": "Bradford", "industry": "manufacturing", "units": "mills", "n_units": 3},
    {"name": "Redgate Hotels", "domain": "redgatehotels.example", "region": "UK", "country": "United Kingdom", "city": "Edinburgh", "industry": "hospitality", "units": "hotels", "n_units": 12},
    {"name": "Ashby Motor Group", "domain": "ashbymotor.example", "region": "UK", "country": "United Kingdom", "city": "Leicester", "industry": "retail", "units": "dealerships", "n_units": 16},
    {"name": "Cavendish Recruitment", "domain": "cavendishrecruit.example", "region": "UK", "country": "United Kingdom", "city": "London", "industry": "services", "units": "offices", "n_units": 7},
    {"name": "Greenfield Veterinary Group", "domain": "greenfieldvets.example", "region": "UK", "country": "United Kingdom", "city": "Norwich", "industry": "healthcare", "units": "practices", "n_units": 27},
    {"name": "Larkspur Fashion", "domain": "larkspur.example", "region": "UK", "country": "United Kingdom", "city": "Manchester", "industry": "retail", "units": "stores", "n_units": 34},
    {"name": "Holloway Freight", "domain": "hollowayfreight.example", "region": "UK", "country": "United Kingdom", "city": "Southampton", "industry": "logistics", "units": "depots", "n_units": 8},
    {"name": "Whitcombe Education Trust", "domain": "whitcombe-trust.example", "region": "UK", "country": "United Kingdom", "city": "Sheffield", "industry": "education", "units": "schools", "n_units": 11},
    {"name": "Thornbury Civil Engineering", "domain": "thornburycivils.example", "region": "UK", "country": "United Kingdom", "city": "Exeter", "industry": "construction", "units": "sites", "n_units": 22},
    {"name": "Veldhuis Groothandel", "domain": "veldhuis.example", "region": "EU", "country": "Netherlands", "city": "Rotterdam", "industry": "wholesale", "units": "warehouses", "n_units": 5},
    {"name": "Nordlicht Energie", "domain": "nordlicht-energie.example", "region": "EU", "country": "Germany", "city": "Hamburg", "industry": "energy", "units": "regions", "n_units": 4},
    {"name": "Marchetti Componenti", "domain": "marchetti-componenti.example", "region": "EU", "country": "Italy", "city": "Turin", "industry": "manufacturing", "units": "plants", "n_units": 3},
    {"name": "Sorensen Maritime", "domain": "sorensen-maritime.example", "region": "EU", "country": "Denmark", "city": "Aarhus", "industry": "logistics", "units": "terminals", "n_units": 6},
    {"name": "Bergstrom Retail", "domain": "bergstrom-retail.example", "region": "EU", "country": "Sweden", "city": "Gothenburg", "industry": "retail", "units": "stores", "n_units": 48},
    {"name": "Alvarez y Prado", "domain": "alvarezprado.example", "region": "EU", "country": "Spain", "city": "Valencia", "industry": "wholesale", "units": "distribution centres", "n_units": 7},
    {"name": "Kowalczyk Logistics", "domain": "kowalczyk-logistics.example", "region": "EU", "country": "Poland", "city": "Poznan", "industry": "logistics", "units": "hubs", "n_units": 11},
    {"name": "Delacroix Sante", "domain": "delacroix-sante.example", "region": "EU", "country": "France", "city": "Lyon", "industry": "healthcare", "units": "clinics", "n_units": 19},
    {"name": "Fischer Praezision", "domain": "fischer-praezision.example", "region": "EU", "country": "Germany", "city": "Stuttgart", "industry": "manufacturing", "units": "machining cells", "n_units": 26},
    {"name": "Brouwer Bouw", "domain": "brouwerbouw.example", "region": "EU", "country": "Netherlands", "city": "Utrecht", "industry": "construction", "units": "projects", "n_units": 31},
    {"name": "Lindqvist Mobler", "domain": "lindqvist.example", "region": "EU", "country": "Sweden", "city": "Malmo", "industry": "retail", "units": "showrooms", "n_units": 21},
    {"name": "Haugen Sjomat", "domain": "haugen-sjomat.example", "region": "EU", "country": "Norway", "city": "Bergen", "industry": "manufacturing", "units": "processing plants", "n_units": 4},
    {"name": "Petrova Pharma Distribution", "domain": "petrova-pharma.example", "region": "EU", "country": "Bulgaria", "city": "Sofia", "industry": "wholesale", "units": "depots", "n_units": 9},
    {"name": "Castellane Hotels", "domain": "castellane-hotels.example", "region": "EU", "country": "France", "city": "Marseille", "industry": "hospitality", "units": "hotels", "n_units": 15},
    {"name": "Rieder Logistik", "domain": "rieder-logistik.example", "region": "EU", "country": "Austria", "city": "Innsbruck", "industry": "logistics", "units": "depots", "n_units": 7},
    {"name": "Van der Berg Verzekeringen", "domain": "vdb-verzekeringen.example", "region": "EU", "country": "Netherlands", "city": "The Hague", "industry": "insurance", "units": "claims teams", "n_units": 5},
]

# The company that carries two deals (used by the ambiguous unlinked meeting). Index into COMPANIES.
SHARED_COMPANY_INDEX = 0

FIRST_NAMES = {
    "United Kingdom": ["James", "Sarah", "Priya", "Daniel", "Charlotte", "Mohammed", "Emma", "Oliver", "Hannah", "Ben", "Rachel", "Kwame",
                       "Lucy", "Chris", "Aisha", "Gareth", "Fiona", "Rory", "Megan", "Sanjay", "Claire", "Jack", "Nadia", "Ruth", "Ewan", "Imogen"],
    "Netherlands": ["Daan", "Sanne", "Bram", "Lotte", "Joris", "Femke", "Pieter", "Anouk", "Ruben", "Maartje"],
    "Germany": ["Lukas", "Anna", "Felix", "Katrin", "Jan", "Miriam", "Tobias", "Lena", "Moritz", "Sabine"],
    "Italy": ["Marco", "Giulia", "Luca", "Francesca", "Alessandro", "Chiara", "Matteo", "Valentina"],
    "Denmark": ["Mads", "Freja", "Emil", "Signe", "Rasmus", "Ida", "Kasper", "Louise"],
    "Sweden": ["Erik", "Elin", "Oskar", "Hanna", "Johan", "Sara", "Anders", "Maja"],
    "Spain": ["Javier", "Lucia", "Carlos", "Marta", "Pablo", "Elena", "Sergio", "Carmen"],
    "Poland": ["Piotr", "Agnieszka", "Marek", "Kasia", "Tomasz", "Magda", "Bartek", "Ola"],
    "France": ["Julien", "Camille", "Antoine", "Elodie", "Nicolas", "Claire", "Mathieu", "Sophie"],
    "Austria": ["Stefan", "Julia", "Markus", "Verena", "Florian", "Lisa"],
    "Norway": ["Henrik", "Ingrid", "Sindre", "Kari", "Magnus", "Silje"],
    "Bulgaria": ["Georgi", "Elena", "Dimitar", "Maria", "Nikolay", "Ivana"],
}

LAST_NAMES = {
    "United Kingdom": ["Hughes", "Patel", "Walsh", "Thompson", "Okafor", "Bennett", "Morgan", "Shah", "Reid", "Clarke", "Doyle", "Fraser",
                       "Mitchell", "Osei", "Chapman", "Begum", "Whitfield", "Lewis", "Hart", "Kaur", "Sutton", "Barlow", "Nash", "Quinn"],
    "Netherlands": ["de Vries", "Jansen", "Bakker", "Visser", "Smit", "Mulder", "Bos", "Vos"],
    "Germany": ["Mueller", "Schneider", "Becker", "Hoffmann", "Wagner", "Koch", "Richter", "Klein"],
    "Italy": ["Rossi", "Conti", "Ricci", "Greco", "Bruno", "Gallo", "Ferrari", "Romano"],
    "Denmark": ["Nielsen", "Jensen", "Andersen", "Larsen", "Pedersen", "Christensen"],
    "Sweden": ["Andersson", "Johansson", "Lindberg", "Karlsson", "Nilsson", "Eriksson"],
    "Spain": ["Garcia", "Fernandez", "Navarro", "Lopez", "Martinez", "Serrano"],
    "Poland": ["Nowak", "Wisniewski", "Zielinski", "Kowalski", "Mazur", "Krawczyk"],
    "France": ["Martin", "Dubois", "Lefevre", "Moreau", "Girard", "Roux"],
    "Austria": ["Gruber", "Huber", "Wimmer", "Steiner", "Leitner"],
    "Norway": ["Hansen", "Berg", "Haugen", "Solberg", "Dahl"],
    "Bulgaria": ["Ivanov", "Dimitrova", "Petrov", "Georgieva", "Stoyanov"],
}

CHAMPION_TITLES = ["Head of Data", "Head of BI", "FP&A Manager", "Finance Director", "Head of Finance Systems", "Group Financial Controller",
                   "Operations Analytics Lead", "IT Director", "Head of Supply Chain", "Commercial Finance Manager"]
EB_TITLES = ["CFO", "CFO", "COO", "VP Operations", "Managing Director", "CIO"]
PROC_TITLES = ["Procurement Lead", "Head of Procurement", "Procurement Manager"]
OTHER_TITLES = ["Data Engineer", "Finance Systems Analyst", "Senior Business Analyst", "Reporting Manager", "Operations Manager"]

DEAL_NAME_PATTERNS = ["{company} data platform", "{company} finance analytics", "{company} reporting replacement", "{company} month-end automation",
                      "{company} operations reporting", "{company} BI consolidation", "{company} Northwind rollout"]
SHARED_DEAL_NAMES = ["{company} finance data platform", "{company} operations analytics expansion"]

UNLINKED_TOPICS = ["connector deep-dive", "weekly sync", "pricing questions", "security review prep", "kick-off planning", "board pack walkthrough"]

MEETING_TITLES = {
    "discovery": ["Discovery call: {company}", "Intro call with {buyer_first} at {company}", "{company} first conversation"],
    "evaluation": ["Platform demo for {company}", "{company} technical review", "Demo: {system} connector and Boards"],
    "proposal": ["Proposal walkthrough: {company}", "{company} commercial review", "Pricing and scope with {buyer_first}"],
    "commit": ["Commercial review with {eb_first}", "{company} contract and timeline", "Final review: {company}"],
}
