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

Speaker convention inside a fragment: a fragment is a list of (who, text) tuples where who is
"rep", "buyer", "eb" (the economic buyer when present), "proc" (procurement) or "it". demo.py maps
each to a real name. Single strings are rep-only or buyer-only lines, as the section says.
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
# mix: (won, lost, open) deals. Win rates follow adoption without being a straight line.
REPS = [
    {"name": "Amira Khan", "email": "amira.khan@northwind-analytics.example", "before": "high", "after": "high", "gaps": [], "rare": [], "mix": (5, 1, 2)},
    {"name": "Tom Ellis", "email": "tom.ellis@northwind-analytics.example", "before": "low", "after": "high", "gaps": [], "rare": [], "mix": (3, 3, 2)},
    {"name": "Jonas Weber", "email": "jonas.weber@northwind-analytics.example", "before": "low", "after": "low", "gaps": [], "rare": [], "mix": (2, 4, 2)},
    {"name": "Sofia Marin", "email": "sofia.marin@northwind-analytics.example", "before": "medium", "after": "medium", "gaps": ["PP"], "rare": ["CH"], "mix": (3, 3, 2)},
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

# Contact 1 is the working contact (champion candidate), contact 2 the economic buyer, contact 3 procurement.
CHAMPION_TITLES = ["Head of Data", "RevOps Manager", "Head of Data", "FP&A Manager", "Head of BI", "Finance Systems Lead", "RevOps Manager"]
EB_TITLES = ["CFO", "VP Ops", "CFO", "COO", "VP Ops", "Managing Director"]
PROC_TITLES = ["Procurement Lead", "Procurement Lead", "Head of Procurement"]
IT_TITLES = ["IT Director", "Head of IT", "Infrastructure Manager"]

DEAL_NAME_PATTERNS = ["{company} data platform", "{company} finance analytics", "{company} reporting replacement", "{company} month-end automation",
                      "{company} operations reporting", "{company} BI consolidation", "{company} Northwind rollout"]
SHARED_DEAL_NAMES = ["{company} finance data platform", "{company} operations analytics expansion"]

UNLINKED_TOPICS = ["Connector deep-dive with {company}", "Weekly sync: {company}", "Pricing questions from {company}",
                   "Security review prep", "Kick-off planning: {company}", "Board pack walkthrough"]

MEETING_TITLES = {
    "discovery": ["Discovery call: {company}", "Intro call with {buyer_first} at {company}", "{company} first conversation"],
    "evaluation": ["Platform demo for {company}", "{company} technical review", "Demo: {system} connector and Boards"],
    "proposal": ["Proposal walkthrough: {company}", "{company} commercial review", "Pricing and scope with {buyer_first}"],
    "commit": ["Commercial review with {eb_first}", "{company} contract and timeline", "Final review: {company}"],
}

CALL_TITLES = {
    "discovery": ["Call with {buyer_first} ({company})", "Discovery call, {company}", "Intro call: {company}"],
    "evaluation": ["Follow-up call: {company}", "Call with {buyer_first} about the evaluation", "{company} evaluation check-in"],
    "proposal": ["Proposal call: {company}", "Call with {buyer_first}, pricing and scope", "{company} proposal questions"],
    "commit": ["Contract call with {buyer_first}", "{company} commercial call", "Call: {company} timeline and paperwork"],
}

# ---------------------------------------------------------------------------
# 2. Rep questions per behaviour tag, buyer statements per element and level
# ---------------------------------------------------------------------------

# Element -> (opening tag, follow-up tags). The follow-up moves the buyer one level up the ladder.
ELEMENT_SCENES = {
    "M": ("asked-metrics", ["quantified-impact", "summarised-and-confirmed"]),
    "E": ("identified-eb", ["asked-eb-access"]),
    "DC": ("mapped-decision-criteria", ["shaped-decision-criteria"]),
    "DP": ("mapped-decision-process", ["agreed-mutual-plan"]),
    "PP": ("asked-paper-process", ["multi-threaded"]),
    "I": ("identified-pain", ["implicated-pain"]),
    "CH": ("tested-champion", ["developed-champion"]),
    "CO": ("named-competition", ["tested-status-quo", "positioned-differentiation"]),
}

# Which elements a skilled rep tends to work in each phase, in preference order.
ELEMENTS_BY_PHASE = {
    "discovery": ["I", "M", "E", "CO", "CH", "DC"],
    "evaluation": ["DC", "M", "E", "CH", "DP", "CO", "I", "PP"],
    "proposal": ["E", "DP", "PP", "DC", "CO", "M", "CH", "I"],
    "commit": ["PP", "E", "DP", "CH", "CO", "M"],
}

REP_QUESTIONS = {
    "asked-metrics": [
        "Before I show you anything, what does {report} look like today in numbers? How long does it take, and where does {kpi} sit?",
        "If this worked exactly as you hope, which number moves? Days to close, {kpi}, something else?",
        "Can you put a figure on it? What is {kpi} today and what has the board asked for?",
        "What do you measure this on at the moment, and how far off target are you?",
    ],
    "quantified-impact": [
        "And what is a point of {kpi} worth to you in money? Rough is fine.",
        "If you got from {pct} to {pct_target}, what does that do to {cost_driver} over a year?",
        "Who owns that number at board level, and what is it costing you right now while it sits below target?",
    ],
    "identified-eb": [
        "Who signs off a spend of this size at {company}? Is that {eb_first}, or someone above?",
        "When it comes to the actual budget decision, whose name is on the approval?",
        "Who ultimately decides, and what will they want to see from us?",
    ],
    "asked-eb-access": [
        "Would it make sense for the three of us to sit down with {eb_first} before we go any further? I would rather hear {eb_first}'s priorities directly.",
        "Can you get me thirty minutes with {eb_first}? I will bring the business case and you can shape it before it goes in.",
        "What would {eb_first} need to see to feel comfortable putting this on the board paper?",
    ],
    "engaged-eb": [
        "{eb_first}, from your seat, what does a successful year look like on {kpi}, and what happens if it stays where it is?",
        "{eb_first}, you have seen more of these projects than I have. What has killed them in the past at {company}?",
        "{eb_first}, if we hit {pct_target} by {go_live}, what does that let you do that you cannot do today?",
    ],
    "mapped-decision-criteria": [
        "When you compare options, what are the must-haves versus nice-to-haves? What would rule a vendor out?",
        "How will you decide between us and anyone else? What is on the scorecard?",
        "What does the finance team need this to do on day one, and what can wait?",
    ],
    "shaped-decision-criteria": [
        "One thing I would add to that list: check whether each vendor needs a consultancy to build the {system} connector. That is where these projects usually stall.",
        "Can I suggest a criterion? Ask every vendor how a {units} manager builds their own report without a ticket to IT. That is the difference between adoption and shelfware.",
    ],
    "mapped-decision-process": [
        "Walk me through the steps from here to a signed order. Who is involved at each step and what do they need?",
        "What has to happen internally before this becomes a yes? Steering group, IT review, a board paper?",
        "If we run the evaluation in the next two weeks, what happens after that, and who is in the room?",
    ],
    "agreed-mutual-plan": [
        "Let me play that back as a plan: evaluation done by {deadline}, {eb_first} sees the summary the week after, procurement in parallel. I will write that up and send it today so we both work to the same dates.",
        "Shall we put dates on each of those steps and share the plan with {eb_first}? That way nobody is surprised in {board_month}.",
    ],
    "asked-paper-process": [
        "Once {eb_first} says yes, what does the paperwork look like? Procurement, legal, security questionnaire, whose paper do we sign on?",
        "Who handles contracts at {company}, and how long does a supplier review normally take? I would rather start that in parallel than at the end.",
        "Is there a spending threshold that triggers a tender or a formal procurement process, and are we above it?",
    ],
    "identified-pain": [
        "What is actually broken today? Not the wish list, the thing that made you take this call.",
        "Where does {report} hurt most: the time it takes, the errors, or the arguments about whose number is right?",
        "What happened recently that made this a priority now rather than next year?",
    ],
    "implicated-pain": [
        "So if that carries on for another year, what does it cost, and who feels it? Is it money, credibility with the board, or people leaving?",
        "What does {eb_first} say when the number is wrong at a board meeting? Where does that land?",
        "If nothing changes by {fy_end}, what does that mean for you personally and for the team?",
    ],
    "tested-champion": [
        "Can I ask you directly: are you willing to make the case for this internally, even if {competitor} comes back cheaper?",
        "What would you need from me to sell this to {eb_first} without me in the room?",
        "Who else inside {company} wants this to happen, and who would rather it did not?",
    ],
    "developed-champion": [
        "I will build you a one-page summary with the {kpi} numbers and the {cur}{money1}k figure so you can walk {eb_first} through it yourself. You should own that story, not me.",
        "Let me give you the three questions to ask {competitor} about the connector. If they answer well, fine, but you should know what to press on.",
    ],
    "named-competition": [
        "Who else are you talking to? {competitor}, an internal build, staying with the spreadsheet?",
        "Is {competitor} in the mix? If so, I would rather know now so we can be straight about where we differ.",
        "What are the alternatives on the table, including doing nothing?",
    ],
    "tested-status-quo": [
        "Honest question: what happens if you do nothing and keep the spreadsheet? Is that a real option for {eb_first}?",
        "The spreadsheet works fine until it does not. When did it last break, and what did that cost?",
        "If the spreadsheet is fine, what made you take this call?",
    ],
    "positioned-differentiation": [
        "Where we differ from {competitor} is the {system} connector: it is ours, maintained by us, no consultancy. Lumen will need {consultancy} for that, and that is where the cost and the timeline drift.",
        "The honest comparison: Lumen's dashboards are pretty; ours let a {units} manager build a report without IT. Ask both of us for a reference where finance runs it themselves.",
    ],
    "secured-next-step": [
        "Can we put the next step in the diary now? {next_day} at {next_time}, you, me and {eb_first}, forty-five minutes on the numbers.",
        "Before we finish, let's agree what happens next and by when. I will send an invite for {next_day} at {next_time}.",
    ],
    "multi-threaded": [
        "Who from IT should join next time? I would like {it_first} to hear the connector answer directly rather than second-hand.",
        "Would it help if I spoke to {proc_first} in procurement separately so you are not the messenger on the contract?",
    ],
    "summarised-and-confirmed": [
        "Let me check I have this right: {n_days} days to close, {kpi} at {pct} against a {pct_target} target, {eb_first} signs, and you want a decision before {deadline}. Anything I have wrong?",
        "So to summarise what you said: the connector is the deal-breaker, {eb_first} decides, and the board is in {board_month}. Fair?",
    ],
}

# Buyer statements per element. Level 1 is vague, level 2 specific, level 3 specific plus owner, money or commitment.
BUYER_STATEMENTS = {
    "M": {
        1: ["We know reporting is slow, everyone complains about it, but I could not put a number on it right now.",
            "It is slower than it should be. I would have to dig out the figures.",
            "There are numbers somewhere, {eb_first} has them, I mostly hear the complaints."],
        2: ["{report} takes {n_days} days to close every month. {kpi} sits at {pct} percent and the target the board set is {pct_target}.",
            "Right now we are at {pct} percent on {kpi} and the target for this year is {pct_target}. And {report} takes {n_days} days, which is {n_days} days of nobody trusting the numbers.",
            "Two numbers matter. {kpi}: {pct} today, {pct_target} target. Days to produce {report}: {n_days}, and {eb_first} wants it at {n_target}."],
        3: ["{eb_name} owns that number. Every point of {kpi} below target is roughly {cur}{money2}k a year in {cost_driver}, so getting from {pct} to {pct_target} is worth about {cur}{money1}k, and it is in next year's budget paper.",
            "We costed it for the board: {cost_driver} ran to {cur}{money1}k last year, and {eb_first} has tied the {pct_target} target to a {cur}{money2}k saving in the {fy_end} plan. That is the number I am measured on.",
            "It is on {eb_first}'s scorecard, not just mine. Going from {n_days} days to {n_target} frees about {n_hours} hours a month per person across {n_people} people, and the {kpi} gap is costing us around {cur}{money2}k a quarter in {cost_driver}."],
    },
    "E": {
        1: ["Budget would come from finance somewhere, I would have to check who actually signs.",
            "Probably {eb_first}, but there might be someone above. I have not asked.",
            "It depends on the amount. Under a certain level I think it can be my budget."],
        2: ["{eb_name}, our {eb_title}, signs anything over {cur}{money2}k. This will need to go past {eb_first}.",
            "{eb_first} signs. {eb_name} is the {eb_title}, and nothing over {cur}{money2}k moves without that signature.",
            "Ultimately {eb_first}. I run the project but {eb_name} holds the budget line for the {units}."],
        3: ["{eb_first} has already told me this is one of three projects on the list for the {board_month} board, and {eb_first} asked me to bring a business case by {deadline}. I can get you thirty minutes with {eb_first} next week.",
            "I spoke to {eb_first} on Monday. {eb_first} wants the {kpi} number fixed before {fy_end} and has set aside budget, but wants to meet the vendor personally. I will set it up for {next_day}.",
            "{eb_name} is sponsoring it. {eb_first} presented the {cur}{money1}k cost of the problem to the board in {board_month} and asked me to find the fix. Happy to bring {eb_first} into the next session."],
    },
    "DC": {
        1: ["It needs to be easy to use, and not too expensive, the usual.",
            "Something that works with what we have and does not need a big project.",
            "We have not written anything down. Good dashboards, decent support, sensible price."],
        2: ["Three things: a native {system} connector, row-level security per {units}, and the finance team being able to build their own reports without IT. Price matters but it comes after those.",
            "The {system} connector is the big one, then single sign-on, then whether the {units} managers can use it without training. If it fails the connector test we do not care about the rest.",
            "We scored the last tool on four things and it failed two, so this time: {system} connector, self-serve for finance, hosting in {region_host}, and a total cost we can defend to {eb_first}."],
        3: ["We wrote the criteria down for the steering group: {system} connector, self-serve for finance, single sign-on, and total cost under {cur}{money2}k a year. Anything that fails the connector test is out regardless of price. {eb_first} signed the list off last week.",
            "There is a scorecard now, weighted. Connector forty percent, self-serve thirty, security twenty, price ten. {it_first} and I built it and {eb_first} approved it, so every vendor gets scored the same way at the {board_month} steering group.",
            "The criteria are agreed and written: {system} connector without a consultancy, finance builds its own reports, {region_host} hosting, and a payback inside twelve months. Those four decide it, and {eb_first} holds us to them."],
    },
    "DP": {
        1: ["We will look at a couple of options and decide when we have seen them.",
            "No formal process. I will make a recommendation and see what people say.",
            "Probably a demo, then a chat with {eb_first}, then we see."],
        2: ["Process is: I shortlist two vendors, we run a two-week evaluation with the finance team, then it goes to {eb_first} and {it_first} from IT for a joint sign-off. We want to decide before {deadline}.",
            "Shortlist by {deadline}, then a four-week evaluation with two {units}, then {eb_first} and {it_first} sign it off together. That is how the last system went through.",
            "Evaluation with the finance team first, then IT security review with {it_first}, then {eb_first} decides. Roughly six weeks end to end if nobody is on holiday."],
        3: ["Steering group meets the first Tuesday of every month. If the evaluation report lands by {deadline}, {eb_first} presents it at the {board_month} board and the decision is minuted there. After that it is purely procurement's timeline.",
            "It is all dated. Evaluation closes by {deadline}, {it_first} gives the security sign-off the week after, {eb_first} takes it to the {board_month} board, and procurement starts the paper the same week. I have shared that plan with {eb_first} already.",
            "We agreed the plan with {eb_first} last week: two-week evaluation ending {deadline}, joint review with {it_first}, board approval in {board_month}, and go-live targeted for {go_live}. Every step has an owner."],
    },
    "PP": {
        1: ["Contracts go through procurement, I have not done one of these before so I am not sure how long it takes.",
            "There is a process, I think. {proc_first} would know.",
            "Legal look at things. I could not tell you how long that takes."],
        2: ["Anything over {cur}{money2}k goes through {proc_name} in procurement, a supplier questionnaire and a legal review of the MSA, usually three to four weeks. It has to be on our paper for data processing.",
            "Above {cur}{money2}k it is a formal supplier onboarding: questionnaire, insurance certificates, then legal review. {proc_first} runs it and it takes about a month.",
            "{proc_first} in procurement owns it. Supplier questionnaire first, then the MSA goes to our legal team, then a DPA because of the data. Three weeks if you answer quickly, six if you do not."],
        3: ["{proc_first} has already sent me the questionnaire, legal reviewed your MSA last week and came back with two clauses, liability cap and the data residency wording. If we agree those, {eb_first} can sign the week after, before the {fy_end} year-end freeze.",
            "The paper is moving. {proc_first} has your questionnaire back, legal has two comments on the MSA, and {eb_first} has a signing slot before {deadline}. Miss that and we hit the {fy_end} freeze and slip a quarter.",
            "We are through procurement. {proc_first} approved you as a supplier on Friday, the DPA is agreed, and the only thing left is the liability wording, which our lawyer said she can close this week. {eb_first} signs after that."],
    },
    "I": {
        1: ["Reporting is a bit of a pain, everyone has their own spreadsheet.",
            "It is slow and people moan about it, but we get there in the end.",
            "Nothing dramatic. It is just untidy and takes longer than it should."],
        2: ["Every month {n_people} people spend about {n_hours} hours each rebuilding {report} by hand from {system} exports, and we still found three errors in it last quarter.",
            "{report} is built by hand from {system} exports. It takes {n_people} people {n_hours} hours each, and the {units} managers get it a week late, so they make decisions on last month's numbers.",
            "The honest answer is that the spreadsheet broke in {board_month}. A lookup failed, {kpi} was reported four points high, and nobody noticed for two weeks."],
        3: ["Last quarter the board got a {kpi} figure that was wrong by four points because a formula broke, and {eb_first} had to correct it at the meeting. That is the moment everyone decided the spreadsheet had to go; it is costing us credibility, not only hours.",
            "It is costing us people. Our best analyst left in {board_month} because the job was rebuilding {report} every month. {eb_first} has said openly that another year like this and the finance team will not hit the {fy_end} audit.",
            "It stopped being an inconvenience when the auditors flagged it. Manual {report}, no audit trail, {n_days} days late. {eb_first} owns the fix personally now, and the {cur}{money1}k of {cost_driver} is the number on the slide."],
    },
    "CH": {
        1: ["I like what I have seen, I can pass it on internally.",
            "I will mention it to {eb_first} when I get the chance.",
            "It is early. Let me see the demo and then I will think about who to talk to."],
        2: ["I have already put this on the agenda for our ops leadership meeting and I have told {eb_first} it is my top project for the next quarter. I will make the case internally.",
            "Yes. I want this. I have spent two years fighting that spreadsheet, and I have told {eb_first} I want it gone by {go_live}. Give me the numbers and I will do the selling.",
            "I am prepared to put my name to it. I have already told {it_first} to expect a security review and I have booked time with {eb_first} for {next_day}."],
        3: ["I have walked {eb_first} through the numbers myself, I have got the {units} managers behind it, and I have already pushed back on {competitor} in the steering group because the connector was not there. My name is on this.",
            "I presented it to {eb_first} and the {units} leads last week without you in the room. Two of them are now asking when they get access. I have also told {proc_first} to start the supplier onboarding so we do not lose {deadline}.",
            "This is my project and {eb_first} knows it. I have taken the {cur}{money1}k business case to the steering group, argued down {competitor} on the connector, and I am the one who gets asked if it slips. So no, I am not going to let it slip."],
    },
    "CO": {
        1: ["We have looked at a few tools over the years.",
            "Nothing serious. A couple of people have mentioned other options.",
            "There is always the option of doing nothing, which is what we have done for three years."],
        2: ["{competitor} demoed to us two weeks ago. The dashboards looked good but they wanted {consultancy} to build the {system} integration, and honestly the spreadsheet works fine for most people here.",
            "We are talking to {competitor} as well. They are cheaper on paper and {it_first} likes them, but the {system} connector was a partner product. The other option is that we keep the spreadsheet, which some people would prefer.",
            "It is you, {competitor}, and doing nothing. Lumen has a slicker demo, I will be honest. But our spreadsheet works fine according to half the {units} managers, so the status quo is a real competitor too."],
        3: ["It is between you and {competitor}. Lumen came in cheaper, around {cur}{money2}k, but they cannot do the {system} connector without a consultancy, and {eb_first} has ruled out another consultancy project. The status quo is still an option for {eb_first} if neither of you can show a payback inside a year.",
            "We scored {competitor} last week and they lost on the connector and on self-serve. {eb_first} has said the spreadsheet is not an option after the {board_month} board error. So it is yours to lose, and the way to lose it is to need a consultancy.",
            "Straight answer: {competitor} is out unless you fall over. They quoted {cur}{money2}k plus {consultancy} for the integration, and {eb_first} refused the consultancy line. Doing nothing was ruled out by the auditors. You are the only option still standing, and I have said so in writing."],
    },
}

# Buyer replies after the rep's follow-up when the buyer accepts the rep's move (used after tags that are not questions).
BUYER_ACKNOWLEDGE = {
    "summarised-and-confirmed": ["Yes, that is it. The only thing I would add is that {it_first} needs to be comfortable with the connector.",
                                 "That is right. And put {deadline} in bold, because {eb_first} will.",
                                 "Correct. You have listened better than the last vendor did."],
    "shaped-decision-criteria": ["That is a fair point. I will add it to the list before the steering group.",
                                 "Good, I had not thought about the consultancy angle. I will ask Lumen the same question.",
                                 "Noted. That will annoy {it_first}, but it is the right question."],
    "agreed-mutual-plan": ["Yes, send it over. If you put names against each step I will forward it to {eb_first} as it is.",
                           "Do that. Dates help me, {eb_first} responds to dates.",
                           "Fine, but leave the board date as {board_month}; I cannot promise earlier."],
    "developed-champion": ["That would help a lot. Keep it to one page, {eb_first} does not read page two.",
                           "Yes please. And put the {cur}{money1}k figure at the top, that is the one {eb_first} remembers.",
                           "Good. Send me those questions and I will ask Lumen on Thursday."],
    "positioned-differentiation": ["That is more or less what {it_first} said after the Lumen demo.",
                                   "I take the point. The consultancy cost is what worries {eb_first} most.",
                                   "Fair. I will put the connector question to both of you in writing."],
    "asked-eb-access": ["I can do that. {eb_first} is in on {next_day}, I will ask for thirty minutes.",
                        "Let me try. {eb_first} is careful about vendor meetings, but with the numbers it should be fine.",
                        "Not yet. Let me get the evaluation done first, then I will bring {eb_first} in."],
    "multi-threaded": ["Yes, I will forward you {it_first}'s details, easier if you two talk directly.",
                       "Fine by me, but copy me on anything to {proc_first}.",
                       "Let me introduce you by email, then it is up to them."],
    "secured-next-step": ["{next_day} works. I will forward the invite to {eb_first}.",
                          "Make it {next_time}, mornings are better for {eb_first}.",
                          "Send it over. I cannot promise {eb_first} yet but I will be there."],
    "tested-status-quo": ["Fair question. It broke in {board_month}, and it cost us about {cur}{money2}k in {cost_driver} before anyone caught it.",
                          "No, it is not really an option. {eb_first} said as much after the last board pack.",
                          "Honestly, for some of the {units} managers it is. That is the fight I am having internally."],
}

# The economic buyer's own statements when present in a meeting (commit or proposal phase). Level 3 quality.
EB_STATEMENTS = [
    "I will be direct: I do not care about dashboards. I care that {kpi} is {pct} and the board expects {pct_target} by {fy_end}. Show me that this gets there and I will sign it. Miss it and I will not renew.",
    "The number I own is {cost_driver}: {cur}{money1}k last year. {buyer_first} tells me you can take a third of that out inside twelve months. If that is true, {cur}{amount_k}k is a decision I can defend.",
    "Two conditions. No consultancy on the connector, because I have been burned by {consultancy} before. And a payback I can show the board in {board_month}. Otherwise we stay on the spreadsheet, ugly as it is.",
    "I have {n_units} {units} and none of them trust {report}. That is the problem. I am less interested in your features than in whether {buyer_first}'s team can run this without ringing you every week.",
]

# Buyer says something useful without being asked; a low-adoption rep usually pitches straight past it.
BUYER_VOLUNTEERED = [
    "Just so you know, {report} took {n_days} days again last month, so there is some urgency here.",
    "By the way, {competitor} is coming in next week to demo. I thought you should know.",
    "One thing before you carry on: {eb_first} has asked me for a number on what this costs us. I do not have one yet.",
    "We had another error in {report} last week, {kpi} was reported two points high. Not a great look for my team.",
    "Our {units} managers keep saying the spreadsheet works fine, so I need something that convinces them, not me.",
]

REP_PITCH_PAST_IT = [
    "Right, yes, that is exactly what Boards fixes. Let me show you the dashboard, it is really visual.",
    "Sure. So, coming back to the platform, the thing customers really love is the drag-and-drop report builder.",
    "Okay. Well, our customers typically see the value pretty quickly. Let me walk you through the modules.",
    "Understood. Let me send you the deck after this, it covers all of that. Now, on pricing tiers, we have three.",
]

# ---------------------------------------------------------------------------
# 3. Small talk, agendas, pitch, logistics, objections, interruptions, closings
# ---------------------------------------------------------------------------

SMALL_TALK = [
    [("rep", "Morning {buyer_first}, thanks for making the time. How is {city} today, still raining?"),
     ("buyer", "Sideways. The car park at the {units} office is a lake. You are in London?"),
     ("rep", "For my sins. Trains were fine for once, so I am counting that as a win.")],
    [("rep", "Hi {buyer_first}, can you hear me okay? My headset has been playing up all morning."),
     ("buyer", "Loud and clear. I have got about forty minutes before I need to jump into the {units} review."),
     ("rep", "That is plenty. I will keep an eye on the clock.")],
    [("rep", "{buyer_first}, hello. How was the half-term break, did you get away?"),
     ("buyer", "Cornwall, in the rain, with two children and a dog. Glad to be back at work, honestly."),
     ("rep", "That sounds familiar. Okay, shall we get into it?")],
    [("rep", "Afternoon {buyer_first}. I saw the {company} announcement about the new {units} last week, congratulations."),
     ("buyer", "Thanks. It is exciting and terrifying in equal measure. More {units}, same finance team."),
     ("rep", "Which is probably why we are talking.")],
    [("rep", "Hi {buyer_first}, thanks for squeezing this in. I know it is month end."),
     ("buyer", "Day {n_days} of it. I am living in {system} exports right now, so your timing is either very good or very cruel."),
     ("rep", "Let us see if we can make it the former.")],
    [("rep", "{buyer_first}, good to see you again. Did the {system} upgrade go in over the weekend?"),
     ("buyer", "It did, mostly. {it_first} has been up since five on Saturday. We are back to normal, more or less."),
     ("rep", "I will not mention that to {it_first} then. Right, shall we start?")],
]

AGENDAS = [
    [("rep", "So the plan for today: I want to understand how {report} works now, what it costs you, and who is involved in changing it. If there is time I will show you a bit of the product, but questions first, is that alright?"),
     ("buyer", "That works. I would rather you understood the mess before you sold me the tidy version.")],
    [("rep", "Before I show anything, can I ask a few questions about the current setup? I have a rough picture from {buyer_first}'s email but I would like the detail."),
     ("buyer", "Go ahead.")],
    [("rep", "Agenda from my side: recap where we got to, go through the open questions on the {system} connector, and then talk about what happens next and who needs to be involved."),
     ("buyer", "Fine. Add pricing to that, {eb_first} has started asking.")],
    [("rep", "I have three things: the numbers, the people, and the process. If we get through those I will have what I need to write something {eb_first} can actually use."),
     ("buyer", "Sounds organised. Let us go.")],
]

PITCH = [
    "So, quick overview. {product} has three parts: Core connects to {system} and pulls everything nightly, or hourly if you want; Boards is where the {units} managers build their own views; and Finance is the month-end pack, which is the bit most customers start with. Everything is hosted in {region_host}, single sign-on, and there is no consultancy needed to set it up.",
    "One thing customers like is the audit trail. Every number in the pack links back to the {system} transaction, so when someone asks where a figure came from, you click it. No more forwarding spreadsheets asking who changed cell F14.",
    "The Boards module is the visual part. Drag a measure onto a canvas, filter by {units}, share a link. A {units} manager can build a view in ten minutes without a ticket to IT, and we have customers where finance has not built a report for the business in a year because the business does it themselves.",
    "On implementation, we say two weeks to first value. Week one is the connector and the data model, week two is rebuilding {report} in Finance. We do that with you rather than for you, so your team knows how it works when we leave.",
    "Pricing is per user with the connector included. For {users} users you are looking at roughly {cur}{amount_k}k a year, which includes hosting in {region_host}, support, and the {system} connector maintained by us. No implementation fee, no consultancy day rates.",
    "We also do scheduled distribution, so {report} goes out to every {units} manager at seven on Monday morning as a PDF and a link. People stop asking finance for the numbers, and finance stops emailing spreadsheets at midnight.",
    "Security-wise we are ISO 27001, data stays in {region_host}, row-level security per {units}, and we plug into whatever single sign-on you have. Most IT teams take a week to clear us.",
    "A customer in {industry} went live with us in {board_month} last year. Same {system} setup as yours, {n_units} sites give or take. Their finance team had {report} out of the spreadsheet in the first month and the {units} managers were building their own views by the second. I can put you in touch with them if that would help.",
    "The other thing worth mentioning is the mobile view. A {units} manager can open Boards on a phone on the way in, see yesterday's {kpi}, and tap through to the transactions behind it. It sounds small but it is the feature people mention when we ask what changed.",
    "We release every two weeks and everything is backwards compatible, so there is no upgrade project. Support is email and chat during UK and European hours, with a named contact for the first ninety days who has done a {system} implementation before.",
    "Just on the roadmap, since people ask: forecasting is coming in the next quarter, so the {report} numbers will carry a projection alongside the actuals. That is included in the subscription, we do not charge for modules that ship after you sign.",
]

LOGISTICS = [
    [("rep", "Can I send the deck across after this, and a link to a sandbox? It is preloaded with a demo {industry} dataset."),
     ("buyer", "Sure, send it to me and I will forward it to the team.")],
    [("rep", "For the demo, who should be in the room?"),
     ("buyer", "Me, maybe {it_first} from IT if I can drag them in. I will let you know.")],
    [("rep", "Do you need an NDA before we share the security pack, or is the questionnaire enough?"),
     ("buyer", "Questionnaire is fine. Send it to me and I will get it to {it_first}.")],
    [("rep", "What is your diary like over the next couple of weeks? I am away Thursday and Friday but free otherwise."),
     ("buyer", "Next week is bad, month end. The week after is better. Send some options and I will pick one.")],
    [("rep", "I will set up a trial tenant for you after this call. It takes a day for the connector, then you can log in."),
     ("buyer", "Okay. Who do I give you for the {system} access? Probably {it_first}.")],
    [("rep", "Would it help if I sent a short summary you can forward internally?"),
     ("buyer", "Yes, one page. People here do not read decks.")],
    [("rep", "Shall I record the demo so the people who cannot make it can watch it back?"),
     ("buyer", "Please. Half the {units} managers will be on the road that day.")],
    [("rep", "Do you want the pricing in {currency}? Some of our EU customers prefer a single currency across the group."),
     ("buyer", "{currency} is fine. Finance will convert it anyway.")],
    [("rep", "Is there a preferred day for these calls? I am conscious Mondays are your {report} day."),
     ("buyer", "Wednesdays or Thursdays. Never a Monday, never the last three days of the month.")],
    [("rep", "I will add {it_first} to the invite for the technical part, unless you would rather ask them yourself?"),
     ("buyer", "Add them. If it comes from me it looks like a project already, and it is not one yet.")],
    [("rep", "Would you like the sandbox loaded with your own {system} export rather than the demo data? It takes an extra day."),
     ("buyer", "Our own data, definitely. The demo data never has our problems in it.")],
]

INTERRUPTIONS = [
    [("buyer", "Sorry, one second, my other line is going."), ("rep", "No problem, take it."), ("buyer", "Right, back. Where were we?")],
    [("rep", "You froze for a moment there, can you say that last bit again?"), ("buyer", "The wifi in this building. I said the target is {pct_target}.")],
    [("buyer", "Apologies, {it_first} is joining late, give me a second to let them in."), ("rep", "Of course. Hi {it_first}, we were just talking about the {system} connector.")],
    [("buyer", "Hang on, someone is at the door. Two seconds."), ("rep", "Sure."), ("buyer", "Sorry. Delivery. Carry on.")],
    [("buyer", "Is that your dog?"), ("rep", "It is, sorry. She has opinions about the postman. Right, where was I.")],
    [("rep", "Sorry, I am going to have to move rooms, someone has booked this one. Bear with me."), ("buyer", "No rush.")],
    [("buyer", "Can I stop you there, I have another call at the top of the hour. Can we do the rest quickly?"), ("rep", "Of course, let me get to the point.")],
    [("rep", "Did I lose you? Your video has frozen."), ("buyer", "Still here. I will turn the camera off, the connection is terrible in this office.")],
    [("buyer", "One moment, {eb_first} has just walked past and wants a word. Two minutes."), ("rep", "Take your time."), ("buyer", "Sorry about that. {eb_first} says hello, and asks when the numbers are coming.")],
]

# Objections: buyer line, strong rep answer (with a behaviour tag), weak rep answer.
OBJECTIONS = [
    {"buyer": "I will be honest, {cur}{amount_k}k a year is more than we expected. {competitor} came in at about {cur}{money2}k.",
     "strong": ("Against the {cur}{money1}k you said the problem costs you, how does {eb_first} weigh that? And does Lumen's number include the {consultancy} work for the {system} connector, because in my experience that is where the real cost sits.", "positioned-differentiation"),
     "weak": "There is some flexibility on price. Let me talk to my manager about a discount if we can sign this quarter."},
    {"buyer": "We are mid year-end. Nobody is going to look at this before {fy_end}.",
     "strong": ("Understood. What does one more year-end on the spreadsheet cost you, though? If we start the paperwork now, you could be live before the next one. Who would need to agree to that?", "implicated-pain"),
     "weak": "No problem at all. I will check back in after {fy_end}."},
    {"buyer": "Honestly, our spreadsheet works fine. It is ugly but people know it.",
     "strong": ("The spreadsheet works fine until it does not. When did it last break, and what did that cost you?", "tested-status-quo"),
     "weak": "Sure, but you would get so much more with proper dashboards. Let me show you the Boards module."},
    {"buyer": "{it_first}'s team is flat out on the {system} upgrade until {go_live}. There is no capacity.",
     "strong": ("Then the connector matters even more: our team installs it in two days, {it_first} approves a service account and that is the whole ask of IT. Can we get {it_first} on a call to confirm that is all we need?", "multi-threaded"),
     "weak": "We can wait until they have capacity, that is fine."},
    {"buyer": "Three years is a long commitment for a tool we have not used.",
     "strong": ("Agreed. What would you need to see at twelve months to be glad you signed for three? Let us write that into the plan and put a review date on it.", "agreed-mutual-plan"),
     "weak": "We could look at a one-year deal, but the price goes up quite a bit."},
    {"buyer": "{eb_first} is nervous about another software project after the {system} rollout overran.",
     "strong": ("What went wrong on that one, specifically? If it was consultancy days and scope, that is the thing we do differently, and I would rather show {eb_first} the evidence than tell you.", "asked-eb-access"),
     "weak": "This is much simpler than an ERP. It will not be like that."},
]

CLOSINGS_STRONG = [
    [("rep", "So, next step. {next_day} at {next_time}, you, me and {eb_first}, forty-five minutes on the {kpi} numbers and the business case. I will send the invite and a one-page summary tonight, and you tell me by Friday if anything in it is wrong."),
     ("buyer", "Fine. I will forward the invite to {eb_first} and warn them it is coming."),
     ("rep", "Thanks {buyer_first}. Speak on {next_day}.")],
    [("rep", "Let me confirm what we agreed: I send the security pack to {it_first} today, you book {eb_first} for {next_day}, and we run the evaluation from the week after. If any of that slips, we tell each other the same day. Deal?"),
     ("buyer", "Deal. Send me the pack and I will chase {it_first}."),
     ("rep", "Perfect. Thanks for your time.")],
    [("rep", "Before we go: the decision date is {deadline}, the paperwork takes three weeks, so we need {eb_first}'s yes by {next_day} at the latest to make it. Can you get that meeting in the diary this week?"),
     ("buyer", "I will try for {next_day} morning. Send me the numbers first."),
     ("rep", "On their way this afternoon. Thanks {buyer_first}.")],
]

CLOSINGS_WEAK = [
    [("rep", "Great, well, I will send the deck over and let us catch up in a couple of weeks."),
     ("buyer", "Okay. Thanks {rep_first}."),
     ("rep", "Thanks {buyer_first}, speak soon.")],
    [("rep", "That is everything from me. Have a look at the sandbox when you get a chance and shout if you have questions."),
     ("buyer", "Will do."),
     ("rep", "Cheers.")],
    [("rep", "I will follow up by email. Let me know when is good for a demo."),
     ("buyer", "Sure. I will check with the team and come back to you."),
     ("rep", "Great, thanks.")],
]

# Meeting-only openers when several buyers are present.
MEETING_OPENERS = [
    [("rep", "Thanks everyone. {buyer_first}, {eb_first}, good to see you both. I will keep the slides to three and spend the time on your questions."),
     ("eb", "Good. I have thirty minutes, then I need to be on a call with the auditors.")],
    [("rep", "Morning all. {eb_first}, we have not met, I am {rep_name} from Northwind. {buyer_first} has been very patient with me over the last few weeks."),
     ("eb", "So I hear. {buyer_first} tells me you are the ones without the consultancy. Prove it.")],
]

# ---------------------------------------------------------------------------
# 4. Emails, notes, meeting summaries
# ---------------------------------------------------------------------------

EMAIL_SIGNOFFS_REP = ["Best,\n{rep_first}", "Thanks,\n{rep_first}", "Kind regards,\n{rep_name}\nNorthwind Analytics"]
EMAIL_SIGNOFFS_BUYER = ["Regards,\n{buyer_name}\n{buyer_title}, {company}", "Thanks,\n{buyer_first}", "Best,\n{buyer_first}"]

# Outbound recap after a call. High adoption cites elements; low adoption is a pleasantry with a deck.
EMAIL_RECAP_HIGH = {
    "subject": ["{company} and Northwind: what we agreed today", "Recap and next steps, {company}", "Notes from today and the plan to {deadline}"],
    "paragraphs": [
        "Hi {buyer_first},\n\nThanks for the time today. Writing down what I heard so you can correct me before it goes any further.",
        "The problem: {report} takes {n_days} days and {n_people} people, and {kpi} is at {pct} against a target of {pct_target}. You put the cost of {cost_driver} at about {cur}{money1}k a year, and {eb_first} owns that number.",
        "Decision: {eb_name} ({eb_title}) signs anything over {cur}{money2}k. The criteria as you described them are the {system} connector without a consultancy, self-serve for finance, and hosting in {region_host}. {competitor} is in the mix and the spreadsheet is the fallback.",
        "Next steps: I send the one-page summary and the security pack to {it_first} tomorrow; you book thirty minutes with {eb_first} for {next_day}; we agree the evaluation dates on that call so we can decide before {deadline}.",
        "If any of that is wrong, tell me. It is easier to fix now than in {board_month}.",
    ],
}
EMAIL_RECAP_LOW = {
    "subject": ["Great to chat", "Northwind deck", "Following up from our call"],
    "paragraphs": [
        "Hi {buyer_first},\n\nGreat to chat earlier. As promised, the deck is attached, along with a short video of the Boards module which I think your team will really like.",
        "A quick reminder of what {product} does: it connects to {system}, builds {report} automatically, and lets the {units} managers build their own dashboards. Customers typically see value very quickly and we do not need a consultancy to set it up.",
        "I have also included a link to the sandbox so you can have a play. It is preloaded with a demo dataset for the {industry} sector.",
        "Let me know when would be a good time for a full demo with the wider team, and feel free to forward this to anyone who might be interested.",
    ],
}
EMAIL_PROPOSAL = {
    "subject": ["Proposal: {product} for {company}", "{company} proposal and pricing", "Northwind proposal, {users} users"],
    "paragraphs": [
        "Hi {buyer_first},\n\nProposal attached as discussed. The headline: {cur}{amount_k}k a year for {users} users, the {system} connector included and maintained by us, hosting in {region_host}, and no implementation fee.",
        "Scope for phase one is {report} rebuilt in Finance, Boards for the {n_units} {units}, and single sign-on. We estimate two weeks to first value and a go-live in {go_live}.",
        "I have written the business case on page two the way {eb_first} asked: {kpi} from {pct} to {pct_target}, {cost_driver} down by a third, payback inside twelve months.",
        "The commercial terms are on our paper with the DPA attached for {proc_first}. Happy to walk through anything on a call, and I would suggest we do that with {eb_first} before {deadline}.",
    ],
}
EMAIL_INBOUND_QUESTION = {
    "subject": ["Question on the security pack", "Re: Northwind, a few questions", "Can you send something for {eb_first}?", "Pricing question", "Reference customers?"],
    "paragraphs": [
        ["Hi {rep_first},\n\nQuick one before I take this to {eb_first}. Two questions came out of the internal discussion yesterday.",
         "First, {it_first} wants to know where the data is hosted and whether the {system} connector needs an open port or works over the API. Second, {eb_first} asked for the total cost over three years including any increases.",
         "If you can turn those around by {next_day} I can include them in the note I am writing for the steering group. Short answers are fine, they will not read more than a page.",
         "Apologies for the short notice. The steering group moved forward a week because {eb_first} is travelling in {board_month}."],
        ["Hi {rep_first},\n\nThanks for the demo. The team liked Boards, although two of the {units} managers said the spreadsheet works fine and they do not see why we would change.",
         "Can you send me two references, ideally {industry} companies with {system}, that I can call? {eb_first} has asked for them before we go any further.",
         "Also, {competitor} sent their proposal yesterday. It is cheaper. I am not saying that decides it, but it will come up, and I would rather have your answer ready than improvise in front of {eb_first}.",
         "Any time this week is fine for a call if that is easier than email."],
        ["Hi {rep_first},\n\n{proc_first} has come back with the supplier questionnaire, attached. There are about forty questions, most of them standard, but the data residency section needs a proper answer for {region_host}.",
         "Legal have also asked whether you will sign on our paper. If not, they need the MSA now so they can start the review, which usually takes three weeks, longer if the liability cap is unusual.",
         "We are trying to get this in front of {eb_first} before {deadline}, so the sooner the better. I have copied {proc_first} so you can deal directly on the questionnaire."],
        ["Hi {rep_first},\n\nI spoke to {eb_first} this morning. The good news is the budget is there. The less good news is {eb_first} wants a written business case with the {kpi} numbers before signing anything.",
         "Could you send me something I can adapt? One page, the {cur}{money1}k cost of {cost_driver}, what changes, and when the payback lands. {eb_first} reads numbers, not adjectives.",
         "I also need to know your earliest start date if we signed in the week of {next_day}, because {it_first} wants to plan the {system} service account around the upgrade."],
    ],
}
EMAIL_DECISION_WON = {
    "subject": ["Good news", "Re: Proposal: {product} for {company}", "We are going ahead"],
    "paragraphs": [
        ["Hi {rep_first},\n\nGood news. {eb_first} signed this afternoon, and {proc_first} will send the countersigned order form tomorrow.",
         "Thank you for the way you ran this. Having the {kpi} numbers and the {cur}{money1}k figure written down made the conversation with {eb_first} a short one, and the connector answer settled {it_first}.",
         "Can we get the kick-off in the diary for the week of {next_day}? I want {report} out of the spreadsheet before {go_live}, and {it_first} has already pencilled in the {system} service account for that week."],
        ["Hi {rep_first},\n\nWe are going ahead. The board approved it in {board_month} and {eb_first} has asked me to get the order signed this week.",
         "Two things for kick-off: {it_first} wants to be on the first call about the {system} service account, and the {units} managers want to see Boards before they get access, so plan a short session for them.",
         "Thanks for your patience with our process. It took longer than either of us wanted, but having the plan written down with dates kept it moving when {proc_first} went on leave."],
    ],
}
EMAIL_DECISION_LOST = {
    "subject": ["Re: Proposal: {product} for {company}", "Decision on the reporting project", "Update from {company}"],
    "paragraphs": [
        ["Hi {rep_first},\n\nI wanted to let you know directly rather than go quiet. We have decided to go with {competitor}. {eb_first} felt the price difference was too big to justify, and {it_first} was comfortable with {consultancy} building the connector.",
         "For what it is worth, I argued for you on the self-serve side, but I could not get the numbers to land with {eb_first} and that was the deciding factor. Nobody here could say what the spreadsheet was costing us, so cheaper won.",
         "Thanks for the time you put in. If Lumen does not work out, I will be in touch."],
        ["Hi {rep_first},\n\nSorry for the slow reply. The project has been put on hold. {eb_first} has frozen new spend until after {fy_end}, and the view internally is that the spreadsheet works fine for another year.",
         "I do not agree with that view, but I could not make the case without a number that {eb_first} owned, and I never got one. The demo was good; the argument for changing was not written down anywhere.",
         "I will come back to you after {fy_end} if the freeze lifts. Please do not chase before then, it will not help."],
        ["Hi {rep_first},\n\nWe are not going ahead this year. The steering group decided in {board_month} to prioritise the {system} upgrade, and there was no appetite for a second project alongside it.",
         "Thank you for the demo and the proposal. Nothing wrong with the product; the timing and the internal bandwidth were against it, and {it_first} could not commit anyone to the connector work until {go_live}.",
         "Please keep me on your list for next year. If you have a customer in {industry} who did this alongside a {system} upgrade, that story would help me next time."],
    ],
}
EMAIL_SCHEDULING = {
    "subject": ["Demo for the {units} managers", "Next week", "Time with {eb_first}"],
    "paragraphs": [
        "Hi {buyer_first},\n\nFollowing up on the demo for the {units} managers. I can do {next_day} at {next_time} or the day after, either for an hour. I will bring our solutions engineer for the {system} questions.",
        "It would help to have {it_first} there for the connector part, and if {eb_first} can join for the first fifteen minutes I will cover the business case at the start rather than the end.",
        "Let me know which works and I will send the invite. I will also send the agenda beforehand so nobody sits through the parts that are not for them.",
    ],
}

NOTES_HIGH = [
    "Call with {buyer_first} ({buyer_title}). Pain: {report} takes {n_days} days, {n_people} people, {n_hours} hours each, errors found last quarter. Metric: {kpi} {pct} vs {pct_target} target, {cost_driver} approx {cur}{money1}k a year. EB: {eb_name} ({eb_title}), signs above {cur}{money2}k, wants a business case by {deadline}. Criteria: {system} connector without consultancy, self-serve, {region_host} hosting. Competition: {competitor} in the mix, cheaper, needs {consultancy} for the connector; status quo is the spreadsheet. Next: one-pager tonight, EB meeting {next_day}.",
    "Internal note after the demo. {buyer_first} is a real champion: has told {eb_first} it is the top project and is willing to argue against {competitor}. Decision process: evaluation to {deadline}, {it_first} security sign-off, {eb_first} to the {board_month} board. Paper: {proc_first} owns supplier onboarding, three to four weeks, MSA on their paper. Risk: two {units} managers say the spreadsheet works fine. Action: get {buyer_first} the three connector questions for Lumen, book {it_first}.",
    "Commercial call notes. {eb_first} confirmed budget and the {pct_target} target by {fy_end}. Conditions: no consultancy, payback inside twelve months. Paper process: questionnaire returned, MSA with legal, two clauses open (liability cap, data residency). Signing slot before {deadline}. Go-live target {go_live}. Next: send liability wording to {proc_first} today, confirm kick-off week with {buyer_first}.",
]
NOTES_LOW = [
    "Good call with {buyer_first}. Interested in Boards, especially the dashboards for the {units}. Sending the deck and the sandbox link tonight. Not sure who else is involved yet, {buyer_first} said they would talk to the team. Follow up in two weeks if I have not heard anything.",
    "Demo went well, {buyer_first} liked the dashboards and asked about scheduled reports. {it_first} from IT asked about hosting and single sign-on. Will send the security pack and the pricing tiers. Need to chase for next steps, nothing booked yet. Might be worth a discount to get it moving.",
    "Spoke to {buyer_first}. Budget is tight this year and {competitor} is also in the running, apparently cheaper. Offered a discount if they can sign this quarter. {buyer_first} will take it to the team. Waiting to hear back, chase on Friday if nothing.",
    "Left a voicemail and sent the proposal over by email. {buyer_first} said {eb_first} would look at it after month end, probably in a couple of weeks. Nothing else to do for now. Follow up next week and see if the deck was forwarded to anyone.",
]

# Summaries for meetings without a transcript (the AI summary a meeting tool would produce).
MEETING_SUMMARY_HIGH = [
    "{rep_name} ran a discovery-style session with {buyer_name} and {eb_name}. {buyer_first} confirmed {report} takes {n_days} days and that {kpi} is at {pct} against a {pct_target} target; {eb_first} put the cost of {cost_driver} at around {cur}{money1}k a year. {rep_first} asked who signs ({eb_first}, above {cur}{money2}k), how the decision is made (evaluation to {deadline}, {it_first} security review, {board_month} board) and what the paperwork involves ({proc_first}, questionnaire and MSA, three to four weeks). {competitor} was discussed; {buyer_first} noted they need {consultancy} for the {system} connector. Next step agreed: {rep_first} sends a one-page business case, {buyer_first} books {eb_first} for {next_day}.",
    "Evaluation review for {company}. {buyer_name} walked through the scorecard ({system} connector, self-serve, security, price). {rep_name} asked what would rule a vendor out and suggested adding the consultancy question, which {buyer_first} accepted. {rep_first} tested whether {buyer_first} would make the case internally; {buyer_first} said it is the top project and {eb_first} already knows. Open risks: two {units} managers prefer the spreadsheet; {competitor} is cheaper. Actions: security pack to {it_first}, evaluation dates confirmed to {deadline}, joint session with {eb_first} on {next_day}.",
]
MEETING_SUMMARY_LOW = [
    "{rep_name} presented the {product} platform to {buyer_name}: Core, Boards and Finance modules, the {system} connector, hosting in {region_host}, and pricing tiers. {buyer_first} asked about hosting and about training for the {units} managers. {rep_first} will send the deck, a sandbox login and the security pack. No next meeting was booked; {buyer_first} will discuss internally and come back.",
    "Demo of {product} for {company}. {rep_name} showed the Boards module and the scheduled distribution of {report}. {buyer_name} mentioned that {competitor} had also demoed and that some of the {units} managers think the spreadsheet works fine; {rep_first} offered a discount if the deal closes this quarter. Follow-up: deck and pricing to {buyer_first} by email.",
]

UNLINKED_SUMMARIES = [
    "Working session on the {system} connector with {buyer_name}. Covered the service account, the nightly load window and how row-level security maps to the {n_units} {units}. {buyer_first} will get {it_first} to confirm the firewall rule.",
    "Short weekly sync. {buyer_first} reported that the evaluation is on track for {deadline} and that {eb_first} has read the one-pager. {rep_first} to send the revised pricing with the three-year option.",
    "{buyer_name} asked how pricing changes if they start with the finance team only and add the {units} managers in {go_live}. {rep_first} walked through the per-user model; {buyer_first} will take the two options to {eb_first}.",
    "Prep for the security review. Went through the questionnaire section by section, especially data residency in {region_host} and the DPA. Attendee from the {company} security team joined for the second half.",
    "Kick-off planning. Agreed the phase one scope, {report} first, Boards for the {units} in the second month, and the training session for the {units} managers. {eb_first} asked for a fortnightly status note.",
    "Walked {buyer_name} through the board pack template built in Finance, showing {kpi} by {units} with the {pct_target} target line. {buyer_first} will trial it for the {board_month} board.",
]
