# Flow Sales: prior art and competitive landscape

Compiled 2026-09-07. Scope: an open-source Claude Code plugin that reads a HubSpot CRM, scores every call/email/meeting on a deal against MEDDPICC with quoted evidence, reports how well a team has adopted the framework and how adoption correlates with won deals, and gives each rep a daily briefing and weekly retro.

Method: Exa web search and page fetches, 2025-2026 material preferred. Every factual claim below carries a URL. Vendor-published numbers are labelled as such. Three source classes to treat with caution are flagged in section 0.3.

---

## 0. Reading guide

### 0.1 One-paragraph verdict

Scoring calls against MEDDIC/MEDDPICC is now table stakes: Gong, Clari, Salesforce, Avoma, Attention, Momentum, Sybill, Oliv, Aviso, People.ai and MEDDICC.com all ship it in some form, and at least a dozen open-source repos do it with Claude. What almost nobody does, in a transparent and reusable way, is (a) measure methodology *adoption as a trajectory* per rep and per element, (b) compute the adoption-to-outcome correlation on the customer's own pipeline, and (c) make every score auditable back to a verbatim quote that a deterministic check has confirmed exists in the transcript. Ebsta (aggregate benchmark reports) and People.ai's Red Hat case study are the closest commercial analogues to (b); Stratyfix is the only product found that does (c) with a deterministic verifier. The sales-training industry meanwhile still sells on before/after business metrics with no adoption instrumentation, and its most-quoted retention statistics ("87% lost in 30 days", "84% in 90 days") trace to a 1979 Xerox/Huthwaite study and to an unsourced Sales Performance International figure respectively.

### 0.2 How to use this document

- Section 1: commercial tools, one entry each, with a summary table first.
- Section 2: open-source / GitHub / Claude Code plugin ecosystem, with a maturity assessment.
- Section 3: sales-training ROI measurement, zombie statistics traced, rigorous evidence, and how consultancies present proof.
- Section 4: fifteen-plus concrete AI-on-CRM use cases as design references, each flagged for outcome evidence.
- Section 5: differentiation notes, the gaps an open, local-first, evidence-quoting, adoption-measuring plugin can own.

### 0.3 Sources to treat with caution

- pulserevops.com "knowledge/q..." pages are dated June 2026 but describe "2027" vendor audits, Forrester Waves and Pavilion benchmarks that cannot be verified. They read as synthetic content. Nothing numeric is cited from them here.
- oliv.ai publishes a large volume of competitor teardown posts (Gong, Clari, Agentforce). Useful for the shape of complaints, but every number in them is unverified marketing.
- Vendor case studies (Force Management, Winning by Design, Sandler, MEDDICC.com, Flow State, People.ai, Nooks) are self-selected and uncontrolled. They are recorded here because the question is how the market presents proof, not whether the proof is sound.

---

## 1. Commercial tools that score deals or calls against MEDDIC/MEDDPICC

### 1.1 Summary table

| Vendor | Methodology scoring | Adoption over time | Ties methodology to outcomes | Public pricing | Notable criticisms |
|---|---|---|---|---|---|
| Gong | AI Deal Reviewer + Methodology Playbooks on Deal Boards (MEDDICC, BANT, SPIN, Challenger, SPICED, Solution Selling, Sandler); AI Scorecard Suggestions | Yes, "see how much your team is applying your methodology overall" via Smart Trackers | Not exposed as a product feature; Gong Labs publishes correlational research | No. Vendr median $54,900/yr, $1,200-2,400/seat/yr plus $5k-50k platform fee | Keyword/embedding trackers, opaque forecast weighting, reps "feel micromanaged", 2025 unbundling raised effective cost 25-56% |
| Clari | Deal Inspection Agent (Feb 2026) scores daily against per-stage criteria; upload your methodology doc to auto-generate criteria | Daily compliance per deal; no published adoption trend view | Opportunity Scoring model correlates factors to closed-won | No. Vendr median $76,000/yr, $1,500-3,000/seat/yr, 25-50 seat minimum | Black-box forecast weighting; premium pricing |
| Salesforce Agentforce / Einstein | Pipeline Inspection ships out-of-the-box MEDDIC/MEDDPICC with qualification gaps and Deal Risk Alerts; Sales Coach grades pitches and role-plays per stage via prompt templates | No adoption reporting found | No | Conversation Insights $50/user/mo; Agentforce for Sales $125/user/mo; Flex Credits $0.10/action | Sales Coach is practice-oriented; heavy dependency on Activity Capture and Data Cloud; consumption pricing hard to predict |
| HubSpot Breeze | Smart Deal Progression suggests updates to default and custom properties (custom via Data Agent) after each recorded call; Conversation Intelligence flags objections/competitors; Deal summaries (beta); buying-committee mapping (public beta) | No | Predictive deal score with top factors | Sales Hub Pro/Enterprise; credits (Pro 3,000/mo, Enterprise 5,000/mo per HubShots); Prospecting Agent $1/lead | Suggestion-only model (rep must approve each field); AI quality depends on CRM hygiene; no methodology scoring per se |
| MEDDICC.com mOS (Deals, Calls, Winni) | MEDDPICC score per deal; Calls generates AI MEDDPICC summary per element; syncs status/notes fields to 20+ CRMs via Merge | Manager "coverage per deal" view; group completion reporting for teams | No | $899/user/yr (individuals and teams 2-10); teams 11+ custom | CRM sync requires pre-created fields with exact values; training-first product |
| Meddicc Score (dgomez, HubSpot Marketplace) | LLM reads last 100 HubSpot engagements, fills framework form, 0-100 score with feedback; supports MEDDICC, MEDDPICC, BANT, SPICED, CHAMP, SCOTSMAN, ANUM, GPCTBA/C&I, FAINT | Reports: average score per rep, deals missing scores, score trends; weekly at-risk emails | No | $69/team/mo (<10 users); 15 users $99/mo; 50 users $299/mo; 30-day trial | Score is a single LLM number; no quoted evidence shown in listing |
| Ebsta | MEDDPICC Deal Qualification Guide (1-10 per criterion with notes); Deal Score and Relationship Score | Adoption tracked and benchmarked in annual reports | Yes, strongest public evidence: 2023, 2024, 2025 benchmark reports | $50-70/user/mo | Salesforce-first; HubSpot supported; small vendor |
| Attention | AI Coaching Scorecards for any framework; Expert Mode rubric prompts that output "Evidence: direct quotes"; CRM auto-update | "Compare rep performance over time by role or call type" | No | Not public; third-party estimates $59-399/user/mo | Intermittent CRM sync bugs (own docs mirror); mid-market focus |
| Momentum | Autopilot extracts MEDDIC/MEDDPICC/BANT fields from calls and emails into Salesforce via natural-language prompts; Classic / Retropilot / Batch; Confirm-to-Write, Write-if-Empty, Automatic | No | No | $69 and $99/user/mo | Salesforce only |
| Rattle | Alerts and CRM Data Agent that "answer or validate key fields"; stuck-in-stage, create/update triggers; Deal Intelligence summaries | No | No | Not public | Salesforce + Slack only |
| Aviso | Sales Methodology module with MEDDIC Score, deal scorecards and templates; MEDDPICC adherence tracking from calls; WinScore | "Sales methodology adherence tracking" in coaching reports (Q1 2025) | WinScore explanations; vendor claims 20% more accurate than reps | Not public | Enterprise; keyword/phrase detection |
| People.ai (rebranded Backstory, April 2026) | ClosePlan scores MEDDPICC completeness 0-100% and answer quality from calls, emails, notes | Yes within Salesforce | Yes: Red Hat 50%+ win-rate lift on deals with >=70% MEDDPICC completion (vendor case) | Not public; ~$50/user/mo, Vendr median $23,100, ~25-seat minimum | Salesforce-centric; 3-month implementations; seat minimums |
| Sybill | CRM Autofill for MEDDPICC/BANT/custom fields after every call and email; HubSpot, Salesforce, Zoho, Dynamics | No | No | Free / $30 / $90 per user/mo (annual); API + MCP on Business | 10-field cap on Business |
| Oliv | CRM Manager Agent scores each criterion cumulatively across the deal; "each score change links to the specific conversation moment"; Coach Agent, Deal Driver briefs | "Methodology coverage by rep" in weekly CRM Health Report | Analyst Agent can answer "compare win rates for deals where X was mentioned" (claimed) | $29/user/mo (annual) | Small vendor; heavy unverified competitor claims |
| Fathom | Summary templates incl. MEDDIC/BANT; CRM field sync; Deal View; coaching metrics and AI scorecards on Business | No | No | Free / $15 / $19 / $25 per user/mo (annual) | Notetaker first; HubSpot 2025 Most Used App |
| Avoma | Deal Methodology (BANT, MEDDICC, SPICED) with AI Methodology Scoring at deal level from "verified evidence"; call scorecards with reasoning and timestamps | Per-rep adherence tracked | Claims "ties scores to outcomes like win rates and quota attainment" and "coaching frequency tied to win rate changes" | $19/$29/$39 recorder seats; CI and RI add-ons $29/seat | Add-on stacking |
| Nooks | Auto-scored calls, AI roleplay, battlecards (SDR/outbound) | Dashboards, heat maps | HubSpot case: 24% pipeline-per-BDR uplift | Not public | Not methodology-oriented |
| Pclub, now Caliber | Training paths, AI role-plays, "platform to measure skill gaps and training ROI" | Skill-gap measurement (LMS-side) | Not published | $997/user/yr | Course-first, not CRM-connected |
| Membrain | Methodology embedded in a CRM/enablement platform; Insight Engine reads process, playbooks, conversations | Behaviour tracking dashboards | Win/loss analytics | Not captured | Stand-alone CRM or Salesforce plug-in; Sweden-based |
| iSeeit | MEDDIC Opportunity Manager native in Salesforce (first MEDDIC app on AppExchange); SalesAI adds automated capture | Traffic-light qualification per opportunity | Vendor claims only | Per user/mo, not public | Salesforce only; small |

### 1.2 Vendor notes

#### Gong
- AI Methodology Playbooks were announced June 2024 for Deal Boards: define MEDDICC, Challenger or SPICED in Gong, AI detects whether each element was discussed and shows "how much your team is applying your methodology overall". AI Scorecard Suggestions auto-answer rubric questions. Smart Tracker assessment tools expose precision and recall, and an engine upgrade "boosts hit rate accuracy by 10%". https://www.gong.io/blog/ai-sales-excellence
- AI Deal Reviewer help doc: pre-built playbooks MEDDICC, BANT, SPIN, Challenger, SPICED, Solution Selling, Sandler; each element is a letter on the deal board with a fulfilment status; elements map to smart trackers; AI suggests notes, the AE reviews and validates. Available on Forecast Essentials and Gong Forecast only. https://help.gong.io/docs/understanding-ai-deal-reviewer
- Deal boards doc (June 2026): Score, Briefs, Warnings, Contacts, Playbook, AI-suggested deal updates for text CRM fields, bi-directional CRM sync. https://help.gong.io/docs/understanding-deal-boards
- Ask Anything answers from up to 60 calls and 500 emails on a deal (10 calls / 80 emails for a contact) and "doesn't take into account any information synced from CRM fields". https://help.gong.io/docs/pipeline-review-ask-anything-about-a-deal-or-account
- Gong's own AE describes prompting Ask Anything with "Assuming the salesperson is using MEDDIC as a framework, analyze this call in bullet format" and pasting the answer into a deal board field. https://www.gong.io/blog/gong-on-gong-expedite-call-review-process-ask-anything
- Oct 2025: AI Data Extractor creates and auto-populates CRM fields from interactions; AI Deep Researcher; Ask Anything extended to whole customer base. https://www.gong.io/press/gong-unveils-new-ai-innovations-to-help-revenue-teams-drive-growth-at-scale
- Nov 2025 deal-review post: "managers can quickly glance at their deal board and immediately see who's following process and which deals might be at risk due to methodology gaps". https://www.gong.io/blog/3-ways-to-use-gong-agents-to-streamline-deal-reviews
- Deal likelihood score is a percentile rank, not a probability; 300+ signals; needs 50 closed-won and 150 closed-lost deals in 2 years and a Forecast seat; not in Gong Pro. https://help.gong.io/docs/explainer-about-deal-likelihood-scores and https://help.gong.io/docs/faqs-for-deal-likelihood-scores
- Under the hood: 50% conversation signals, 50% activity/contacts/timing/history; "21% more precise than sales reps" at week 4. https://help.gong.io/docs/explainer-under-the-hood-of-deal-likelihood-scores
- Pricing: Vendr median $54,900/yr across 1,126-1,130 purchases, range $11,352-$204,036, $1,200-2,400/seat/yr, 14% average discount. https://www.vendr.com/marketplace/gong . March 2025 unbundling moved Forecast, Engage, Enable and Data Cloud into paid modules; effective per-user cost up 25-56% 2023-2026 per revenue.io's analysis. https://www.revenue.io/blog/what-does-gong-actually-cost . Platform fee $5,000-50,000 and ~15-seat minimum. https://www.claap.io/blog/gong-pricing
- Criticisms: a G2 verified reviewer quoted as "Many reps also resist using Gong because they feel micromanaged, leading to low adoption" and an enablement director: "It can be overwhelming to set up trackers. AI training is a bit laborious". https://www.oliv.ai/blog/gong-alternative-limitations-beyond-meeting-intelligence . "I don't know where my weighted number comes from" reported as a common G2 complaint about forecast. https://oliv.ai/blog/gong-forecasting . gtm-pod: "Adoption tax: bought widely, used narrowly without a coaching program owner"; always-on recording triggers legal review in EU/CA/IL. https://gtm-pod.com/tools/gong . Gong Forecast rated ~4/10 in a 600-review analysis. https://thecroreport.com/tools/gong/
- Gong Labs research used by everyone: 1.8M opportunities, closed-won deals have 2x the buyer contacts; multi-threading boosts win rates 130% on deals over $50K. https://www.gong.io/blog/the-best-sales-insights-of-2025

#### Clari
- Deal Inspection Agent (community doc, Feb 2026): monitors opportunities daily, evaluates against per-stage qualification criteria; "Upload your sales methodology document to auto-generate criteria"; reads RevDB plus transcripts and emails; falls back to RevDB fields alone; SQL-style target rules; org starts with agents disabled. https://community.clari.com/ai-chatgpt-and-revai-83/configuring-the-ai-deal-inspection-agent-2871
- Copilot Smart CRM Suggestions populate decision criteria, economic buyer, next steps from conversations. https://community.clari.com/best-practices-learnings-wins-tips-70/
- MEDDPICC mapped onto Clari objects (Team Roles for EB and Champion, milestones for Decision Process and Paper Process); MEDDPIC dashboards from field data. https://community.clari.com/best-practices-learnings-wins-tips-70/meddpicc-and-clari-936
- CRM/Opportunity Scoring whitepaper: two years of opportunity history plus conversation data, weighted to closed-won. https://pages.clari.com/rs/866-BBG-005/images/CRM%20Scoring%20Whitepaper.pdf
- Pricing: Vendr median $76,000/yr (291 purchases), $1,500-3,000/seat/yr, 25-50 seat minimum, "often 15-30% higher than Gong". https://www.vendr.com/marketplace/clari

#### Salesforce (Einstein Conversation Insights, Pipeline Inspection, Agentforce Sales Coach)
- Pipeline Inspection: new Alerts column with "single-threaded contacts, pushed deals, and activity drops", "out-of-the-box sales methodology support (think MEDDIC and MEDDPICC)" so reps see qualification gaps; Enterprise Edition+ on Agentforce for Sales; alerts require opportunity scoring, EAC or ECI to be active. https://www.salesforce.com/sales/latest-release/
- Agentforce Sales Coach: pitch practice and role-play; Opportunity Coaching sub-agent with prompt templates per stage (Qualification, Needs Analysis, Discovery, Proposal/Pricing, Negotiation/Review); needs Agentforce, Einstein Generative AI, Agentforce Studio and Data 360 for RAG. https://trailhead.salesforce.com/content/learn/modules/agentforce-for-sales-coaching-setup-and-customization/get-to-know-agentforce-sales-coach
- March 2026 Agentforce Sales: pipeline management agent "proactively updates fields and recommends next steps"; account research and meeting prep agent; prospecting agent. https://www.salesforce.com/news/stories/agentforce-sales-announcement/
- Pricing: Conversation Insights $50/user/mo; Agentforce for Sales $125/user/mo; Sales Programs $100. https://www.salesforce.com/sales/conversation-intelligence/pricing/ . Flex Credits $500 per 100,000, 20 credits ($0.10) per action. https://www.salesforce.com/uk/news/press-releases/2025/05/15/agentforce-flexible-pricing-news/ . A third-party 2026 guide lists Agentforce Sales Enterprise $175, Unlimited $350, Agentforce 1 $550 per user/mo and notes "consumption pricing is genuinely hard to predict". https://salesforcedictionary.com/blogs/agentforce-sales-complete-2026-guide
- Criticism (competitor-sourced): Sales Coach "analyzes practice sessions, not live calls", requires Data Cloud and admin prompt engineering to reflect MEDDIC. https://www.oliv.ai/blog/agentforce-sales-coach
- Salesforce's own enablement story: proactive, context-aware guidance via Data Cloud, Slack and Sales Coach credited with "$37M in combined pipeline and revenue" (self-reported). https://www.salesforce.com/blog/ai-sales-enablement/

#### HubSpot Breeze
- Smart Deal Progression: after a recorded meeting, "suggests CRM changes to both default and custom properties (custom property updates are powered by Data Agent), drafts contextual follow-up emails, and surfaces next steps"; reps "review, refine as needed, and apply with one click"; Sales Hub and Service Hub Professional/Enterprise. https://www.hubspot.com/products/sales/smart-deal-progression
- Knowledge base (Aug 2026): recommendations from Notetaker, Google Meet/Teams/Zoom syncs, AI call summaries or connected-app transcripts; approve or reject suggested property updates; Breeze Assistant meeting agendas. https://knowledge.hubspot.com/sales-tools/use-ai-to-close-deals-faster
- Spring 2026 Spotlight: Smart Deal Progression public beta; buying-committee mapping agent public beta; Prospecting Agent $1 per recommended lead; Customer Agent $0.50 per resolution. https://www.hubspot.com/spotlight/grow-revenue
- Tier details from a third-party review: Deal summaries (Beta) on Professional; AI call transcript enrichment (Beta) on Enterprise; mandatory onboarding fees $1,500-7,000. https://www.default.com/post/hubspot-breeze-ai-review-and-pricing . Credits: Pro 3,000/mo, Enterprise 5,000/mo; Sales Workspace has Guided Actions and Predictive Deal Score. https://www.hubshots.com/episodes/episode-317
- Conversation Intelligence flags objections, competitor mentions, pricing discussions, committed next steps in the deal record; predictive lead score shows top driving factors. https://toolixlab.com/blog/hubspot-ai-review-2026
- RevOps critique: "AI writing to production CRM records automatically, every time a sales call ends" and the audit to run before enabling. https://resources.rework.com/news/sales-tech/hubspot-spring-2026-smart-deal-progression-aeo-revops
- Limitation stated by AskElephant: "operate on a suggestion model, requiring reps to manually approve every suggested update". https://www.askelephant.ai/blog/how-does-hubspot-use-ai-breeze
- Conversation summaries are editable, with persona templates and a Breeze Q&A bar. https://www.sidekickstrategies.com/hubspot-updates/updated-conversation-summaries-calls-meetings
- Official remote MCP server at mcp.hubspot.com with read/write on CRM objects and engagements (calls, emails, meetings, notes, tasks); OAuth; sensitive-data properties excluded. https://developers.hubspot.com/ai-tools/mcp
- HubSpot Agent CLI (`hubspot`, distinct from `hs`) for Claude Code/Cowork/Codex, plus official skills repo. https://developers.hubspot.com/docs/developer-tooling/local-development/agent-cli/guide and https://github.com/hubspot/agent-cli-skills

#### MEDDICC.com (Andy Whyte) mOS: Deals, Calls, Winni
- Deals: "clear, visual MEDDPICC scoring for every deal"; managers "coach on evidence"; Winni generates an AI-structured MEDDPICC summary from linked calls. https://meddicc.com/products/deals
- CRM sync via Merge to 20+ CRMs; each element needs a Status field (strong/medium/low, exact internal values) and a Notes field created in advance; HubSpot via Private App with listed scopes; imports deals updated in last 2 years. https://meddicc.com/knowledge/setting-up-your-crm-integration
- Pricing: MEDDPICC Masterclass $499; membership $899/user/yr for individuals and teams of 2-10 (includes Deals, Calls, Winni, group completion reporting); 11+ custom. https://meddicc.com/pricing
- Positioning piece (June 2026): "A tool that lives outside your CRM is a tool your reps will quietly stop using. Double entry kills adoption faster than anything else." https://meddicc.com/resources/meddic-software-apply-meddpicc-to-every-deal-meddicc
- Whyte's implementation post: added confidence scoring per letter 6 months in, then had to add written definitions per score level because optimism varied by rep ("Happy Ears and the Pessimists"); gated Negotiation stage on Decision Process >= 8/10. https://meddicc.medium.com/lessons-learned-from-implementing-meddpiccr-a-year-on-25cafef1330b

#### Meddicc Score (HubSpot Marketplace app by dgomez)
- Pulls the last 100 deal engagements from HubSpot, uses an LLM to answer framework questions, pre-fills the form, then scores 0-100 with feedback, risks and next steps; score stored as a HubSpot custom property; workflow actions; weekly at-risk emails; reports of average score per rep and score trends. Model-agnostic (OpenAI, Google, Anthropic, GPT-OSS). https://meddiccscore.com/hubspot/ and https://ecosystem.hubspot.com/marketplace/listing/meddicc-score
- Pricing: Premium $69/team/mo (<10 users); 15 users $99/mo; 20 users $129; 25 users $159; 50 users $299; 30-day trial. https://meddiccscore.com/
- This is the closest existing HubSpot-native analogue to Flow Sales. It shows a number and feedback, not quoted evidence per element, and it has no adoption-over-time or outcome-correlation reporting beyond per-rep averages.

#### Ebsta
- 2025 Sales Qualification Report (655,000 opportunities, $48B): well-qualified deals 6.3x more likely to close and close 21.6% faster; high qualification scores drive 50% win rates vs 8% for poorly qualified; only 36% of deals past Discovery have both a score and notes; strongly qualified deals 1.9x less likely to slip. https://www.ebsta.com/news-updates/new-ebsta-report-sales-qualification/
- H1 2024 benchmarks: methodology adoption up 19% since 2023; 68% of deals past qualification "not qualified effectively"; top performers 357% more likely to use a methodology; 75% of closed-won had MEDDPICC completed; 324% more likely to win if MEDDPICC completed by Solution Presented; 5.6 meetings to reach >80% MEDDPICC. https://www.ebsta.com/wp-content/uploads/2024/07/H1-Update-2024-B2B-Sales-Benchmarks.pdf
- 2023 report (3.2M opportunities, 364 companies, $37B): methodology adoption doubled 11% to 21%; MEDDPICC used by 61% of adopters; only 15% of opportunities fully qualified and just 5% of companies score confidence per criterion; "when fully utilized, win rates increased by 311%"; Metrics, Decision Criteria and Paper Process least populated but highest impact (+206% together); one logistics company +23% win rate after introducing scored MEDDPICC in weekly pipeline reviews. https://www.ebsta.com/wp-content/uploads/2023/02/2023-B2B-Sales-Benchmark-Report.pdf
- Single-customer teardown: MEDDPIC used on 26% of closed opps; 45% win rate with vs 18% without; win rate by cumulative "Big 4" score band and stage (0-4 = 19% at Discovery, 13-16 = 92% at Negotiation); "lower performers consistently discover more as deal progresses versus high performers having reached full discovery at Formal Proposal". https://www.ebsta.com/wp-content/uploads/2023/10/Ebsta-x-Sprocketeer-Insight-Report-Teardown-INBOUND-Edition.pdf
- HubSpot case (Cappy): MEDDPICC previously "happened inconsistently outside of HubSpot"; weekly "Deal Team" meeting reviews MEDDPICC; reduced admin time and "increased their usage" (no numbers). https://www.ebsta.com/case-study/cappy/
- Pricing $50/user/mo Revenue Intelligence, $60 Conversation Intelligence, $70 full; 14-day trial. https://www.softwareadvice.com/crm/ebsta-profile/ , https://www.gtmlabz.io/tools/ebsta , https://www.ebsta.com/pricing/

#### Attention
- Scorecards "for any framework" (MEDDIC, BANT, SPICED, custom), per role/call type; "compare rep performance over time"; alerts when a call scores below threshold. https://www.attention.com/product/ai-coaching-scorecards
- Scorecard creation guide with an Expert Mode prompt template whose output format is `Score / Evidence: [Direct quotes from transcript] / Reasoning`, and a MEDDIC Discovery Scorecard template (8 items with weights). https://www.attention.com/center-of-attention/coaching-scorecards-explained
- CRM auto-update: map call notes to fields, append or overwrite, custom fields, Salesforce and HubSpot. https://www.attention.com/product/crm-auto-update
- Pricing not published; a community platform guide lists Starter ~$59, Professional ~$149, Enterprise ~$399 per user/mo and notes "intermittent sync bugs". https://github.com/sales-skills/sales/blob/main/skills/sales-attention/references/platform-guide.md . ToolChase estimates $100-200/user/mo. https://toolchase.com/tool/attention-tech/
- Attention open-sourced its rubric layer as gtm-superintelligence (section 2).

#### Momentum
- "Automate MEDDIC, MEDDPICC, and BANT in Salesforce". https://www.momentum.io/meddic-autopilot
- Autopilot docs are the best public description of field-extraction engineering: Classic (per call), Retropilot (on record events, look back over a window), Batch (backfill new methodology fields); per-field-type prompt rules; "Silence = output nothing", "No over-extraction (inferring content not in the transcript)"; save behaviours Confirm to Write (weeks 1-2), Write if Empty (default), Automatic Write. https://docs.momentum.io/ai-prompting-autopilot and https://docs.momentum.io/autopilot-classic-setup
- Pricing: Business $69, Transformation $99 (adds AI coaching, exec briefs), Enterprise custom. https://www.momentum.io/pricing . Ramp testimonial: "cut the time in half for our sellers to progress their deals in Salesforce". https://www.momentum.io/feature-autopilot-suite

#### Rattle
- CRM Data Agent "answer or validate key fields... review the reasoning behind each suggestion"; Revenue Pulse and Manager Rundown agents; testimonial "30% more accurate with our forecasting since Rattle flags data hygiene issues". https://www.gorattle.com/
- Workflows: create/update triggers, moment-in-time, stuck-in-stage alerts, Slack action buttons; Deal Intelligence summaries from CRM fields, Gong/Zoom/Chorus calls, Slack deal rooms and logged emails; Salesforce and Slack only. https://help.gorattle.com/en/articles/5671362-using-create-update-workflows and https://help.gorattle.com/en/articles/9214845-how-do-i-set-up-deal-intelligence

#### Aviso
- Sales Methodology module: Engagement Grade, Aviso AI Score, MEDDIC Score, deal scorecard and templates. https://dochelp.aviso.com/en_US/sales-methodology/sales-methodology
- MEDDPICC data gathered by "detecting essential keywords, phrases, and cues", bidirectional CRM sync, MIKI chat. https://www.aviso.com/blog/aviso-ai-powered-meddpicc-adherence
- Q1 2025: coaching reports with "sales methodology adherence tracking (e.g., MEDDIC)" and custom pitch models. https://www.aviso.com/blog/aviso-ai-product-updates-q1-2025
- Opportunity Scoring Agent: score trajectory chart, top factors incl. "incomplete MEDDPICC fields", recommended actions, cadences. https://www.aviso.com/blog/how-to-know-which-deals-deserve-your-time . WinScore claims: 20% more accurate, 32% more precise than reps, 71% recall by week 4. https://www.aviso.com/blog/win-more-deals-with-aviso-ai-winscores

#### People.ai (Backstory since April 2026)
- ClosePlan "analyzes dozens, potentially hundreds, of calls, emails, chats, meetings, transcripts, and CRM notes to score completeness from 0-100% and assess answer quality from low to high". https://pipeline.zoominfo.com/sales/people-ai-review
- Red Hat: MEDDPICC embedded in CRM, AI surfacing missing economic buyers and engagement gaps, "50%+ increase in win rates on deals with 70%+ MEDDPICC completion", 2,000 sellers. https://www.backstory.ai/case-studies/red-hat
- Pricing: no rate card; ~$50/user/mo; Vendr median ~$23,100; often ~25-seat minimum; implementations closer to 3 months than the marketed 2-4 weeks. https://leadhaste.com/blog/peopleai-pricing-2026 and https://leadhaste.com/blog/peopleai-review-2026 . Open API and MCP with the Backstory rebrand. https://www.technologyinsales.com/tools/people-ai

#### Sybill
- CRM Autofill: "autofills MEDDPICC, BANT, and custom CRM fields", backfills last 30 deals, per-deal-type and per-stage conditional fields, test before go-live. https://help.sybill.ai/en/articles/11899540-crm-autofill-feature-guide and https://help.sybill.ai/en/articles/9969597-crm-deal-summaries
- Pricing: Free; Pro $30; Business $90 (CRM Autofill 10 fields, API + MCP, "Connect Sybill to Claude"); Enterprise unlimited. https://www.sybill.ai/pricing
- HubSpot MEDDPICC how-to. https://www.sybill.ai/blogs/auto-update-meddpicc-bant-fields-hubspot-call-notes

#### Oliv
- Auto-scoring design: "not based on a single call but accumulated across the full deal lifecycle... Each score change links to the specific conversation moment that triggered it"; recommends a 2-week parallel test against manual manager scores; claims 94% MEDDIC completion vs 15-30% manual baseline. https://oliv.ai/blog/meddic-auto-scoring-sales-methodology-enforcement
- Brief cadence: Morning Brief 30 min before each call, Sunset Summary every evening, Weekly Forecast one-pager Monday, delivered to Slack/email; "Evidence Logs for full audit trails". https://www.oliv.ai/blog/oliv-ai-features-platform-guide-head-of-sales
- RevOps guide: weekly CRM Health Report with "Methodology coverage by rep"; Analyst Agent example queries such as "Compare win rates for deals where Clari was mentioned vs. not". https://oliv.ai/blog/oliv-ai-revops-implementation-admin-guide
- Pricing $29/user/mo annual, no platform fee. https://www.oliv.ai/pricing

#### Fathom
- Pricing: Free unlimited recording; Premium $15-16; Team $15-19; Business $25 annual ($34 monthly) adds CRM field sync, Deal View, coaching metrics and AI scorecards; "Claude & ChatGPT integrations", public API and MCP; 15+ templates incl. BANT and Sandler. https://www.fathom.ai/pricing
- HubSpot custom field mapping live, Salesforce rolling out; Deal View aggregates every call on a deal. https://www.fathom.ai/integrations-crm . HubSpot's 2025 Most Used App, 20,000+ marketplace installs. https://ecosystem.hubspot.com/marketplace/listing/ai-notetaker-by-fathom

#### Avoma
- Deal Methodology config: default BANT, MEDDICC, SPICED (non-editable) plus custom; AI Conversation Scoring per call and AI Methodology Scoring at deal level "using verified evidence from meetings and emails". https://help.avoma.com/configure-deal-methodology
- Call scoring "with reasoning and timestamps tied to call moments". https://www.avoma.com/conversation-intelligence/sales-call-scoring-software
- Claims to tie scores to outcomes: "ties scores to outcomes like win rates and quota attainment... Coaching frequency tied to win rate changes across teams and deal stages". https://www.avoma.com/conversation-intelligence/real-time-sales-guidance-software . 0-100 qualification score per deal. https://www.avoma.com/revenue-intelligence/sales-performance-management-software
- Pricing: $19/$29/$39 per recorder seat (annual), viewers free; Conversation Intelligence and Revenue Intelligence add-ons $29/seat (annual). https://www.avoma.com/pricing and https://help.avoma.com/avoma-pricing-recorder-seats-free-users-add-ons

#### Nooks
- Auto-scores every call, roleplay bots built from real calls, heat maps. https://www.nooks.ai/ai-coaching . HubSpot case: 59% more live conversations, 24% pipeline-productivity-per-BDR uplift, ramp 6 to 4 months. https://www.nooks.ai/customer-success/hubspot . UserEvidence-verified survey: 54% conversation-to-meeting lift after bot training. https://www.nooks.ai/
- SDR/outbound oriented; not a MEDDIC tool.

#### Pclub (rebranded Caliber)
- $997/user/yr; expert courses, AI role-plays, "a platform to measure skill gaps and training ROI"; CEO Chris Orlob (ex-Gong). https://www.caliber.io/pricing and https://www.caliber.io/ . Orlob's discovery framework is drawn from ~2,500 manually reviewed calls and Gong data-science work. https://getlatka.com/interviews/pclubio-chris-orlob-2023

#### Membrain
- "Sales Enablement CRM" that embeds methodology into process; partner network of trainers who embed their methodologies; Insight Engine "understands your defined sales process, your playbooks, your pipeline behavior, and your real customer conversations". https://www.membrain.com/ and https://www.membrain.com/sales-enablement . Baseline Selling page cites "less than 10% of all salespeople use [selling processes] effectively" (no source). https://www.membrain.com/baseline-selling

#### iSeeit
- "The Official and First MEDDIC app on Salesforce.com": qualifiers embedded in the opportunity layout, org chart, close plan, traffic-light forecast; per user/mo. https://appexchange.salesforce.com/appxListingDetail?listingId=a0N3000000Dpa1UEAR and https://now.iseeit.com/meddic-salesforce/
- Oct 2025 "SalesAI" post claims automated MEDDIC capture, real-time risk score, "up to 90% accuracy" and "25-30%" forecast improvement (no data shown). https://now.iseeit.com/how-can-ai-help-sales-teams-qualify-opportunities-with-meddic/

#### Other relevant products surfaced
- Stratyfix: "Click any score and the exact transcript line that earned it lights up. A deterministic check verifies every quote against the transcript... if the quote isn't really in the transcript, the score doesn't ship"; versioned scores; propose-only actions; calibration switches on at the 200th scored conversation. https://stratyfix.com/
- Airspeed: flagged moments with "a timestamp, the exact transcript line, and the specific coaching point"; cross-checks Claude, GPT and Gemini to reduce false flags; claims 40% faster ramp. https://www.goairspeed.com/blog/how-ai-finds-coaching-moments-in-sales-calls and https://www.goairspeed.com/academy/platform/ai-coaching
- Halo AI: benchmarks reps against top performers with transcript citations. https://www.haloagents.ai/solutions/use-cases/ai-call-reviews
- Weflow: Salesforce-native warning triggers (no activity, ghosted, stalled in stage, close date pushed) with thresholds scaled to sales-cycle length, plus methodology-field-empty warnings. https://www.weflow.ai/blog/deal-health-signals-framework
- Winn.ai (real-time playbook adherence MEDDIC/BANT/SPICED), Scratchpad (Salesforce Hygiene Monitor, $0-49), Proshort, Bliro, MaxIQ, Revenue.io, Salesken are catalogued in the sales-skills router README. https://github.com/sales-skills/sales
- AskElephant writes field-level MEDDIC/buyer-committee data to HubSpot custom properties without rep involvement. https://www.askelephant.ai/blog/top-hubspot-properties . Demodesk custom MEDDICC summary skill syncing to HubSpot meeting notes. https://demodesk.com/blog/how-to-set-up-a-custom-summary-skill-to-extract-meddicc-data-and-sync-to-hubspot

### 1.3 What "adoption" means in each product (definitions matter for Flow Sales)

The word is used for at least five different measurements. Flow Sales needs to pick one, or report several explicitly.

| Product / source | Unit measured | How measured | Trend over time? |
|---|---|---|---|
| Gong AI Methodology Playbooks | Was each MEDDICC element *discussed* on a deal's conversations | Smart Tracker hit per element, AE-validated note | Yes, "how much your team is applying your methodology overall" on Deal Boards (Forecast seat) |
| Ebsta benchmark reports | Was each MEDDPICC criterion *filled and scored* on the opportunity | CRM field population plus 1-10 confidence score | Cross-sectional per report year; per-customer teardown by rep and by stage |
| CSO Insights 2019 | Share of the *sales force using the methodology daily* | Manager survey (self-report) | Annual study only |
| People.ai / Backstory ClosePlan | *Completeness* 0-100% and *answer quality* low-high per deal | LLM over calls, emails, notes, CRM | Within Salesforce dashboards |
| Avoma | *Adherence per call* against scorecard and *deal-level* methodology score from evidence | LLM scoring with timestamps | Per-rep adherence tracking; claims outcome tie |
| Oliv | *Coverage by rep* (fields populated) | Weekly CRM Health Report | Week-over-week pipeline hygiene trend |
| Attention | *Scorecard score per call*, per framework item, weighted | LLM against rubric with quoted evidence | "Compare rep performance over time by role or call type" |
| Meddicc Score | *Average score per rep* and *deals missing scores* | LLM 0-100 from last 100 engagements | Score trend reports, weekly emails |
| Force Management / Sandler / Flow State | Reps *trained or certified* | Attendance, certification | Not tracked post-training |

The distinction that matters most: field completion (Ebsta, People.ai, Oliv) can be gamed by a rep typing "TBD" into a box, and discussion detection (Gong) can fire on the rep merely *mentioning* an economic buyer. Only evidence-scored adherence (Attention, Avoma, Stratyfix, the open repos) measures whether the rep actually did the thing on the call, and none of those report it as a team trajectory tied to outcomes.

### 1.4 Consolidated pricing reference (public or third-party benchmarked, 2025-2026)

| Vendor | Published price | Benchmarked or estimated | Minimums / fees |
|---|---|---|---|
| Gong | None | $1,200-2,400/seat/yr; median contract $54,900/yr (Vendr, 1,126 purchases) | Platform fee $5k-50k/yr; onboarding $2k-10k+; ~15 seats; annual only; 5-15% renewal uplift |
| Clari | None | $1,500-3,000/seat/yr; median $76,000/yr (Vendr, 291 purchases) | 25-50 seat minimum; implementation fees |
| Salesforce | Conversation Insights $50/user/mo; Agentforce for Sales $125/user/mo; Flex Credits $500 per 100k ($0.10/action) | Third-party: Agentforce Sales tiers $175 / $350 / $550 | Requires Sales Cloud Enterprise+; Data Cloud for RAG |
| HubSpot Breeze | Included in Sales Hub Pro/Enterprise; Prospecting Agent $1/lead; Customer Agent $0.50/resolution | Sales Hub Pro ~$450/mo (5 users), Enterprise ~$1,500+/mo | Credits: Pro 3,000/mo, Enterprise 5,000/mo; onboarding $1.5k-7k |
| MEDDICC.com | $499 masterclass; $899/user/yr membership (1-10 users) | Teams 11+ custom | CRM sync only on team plans |
| Meddicc Score | $69/team/mo (<10 users); $99/mo for 15; $299/mo for 50 | | 30-day trial |
| Ebsta | $50 / $60 / $70 per user/mo | | 14-day trial |
| Attention | None | $59 / $149 / $399 per user/mo (community guide); $100-200 (ToolChase) | Annual; demo-gated |
| Momentum | $69 / $99 per user/mo; Enterprise custom | | Discounts at 50+ users; minimum thresholds |
| Rattle | None | | Salesforce + Slack only |
| Aviso | None | | Enterprise |
| People.ai / Backstory | None | ~$50/user/mo; median $23,100/yr (Vendr); range $2,316-116,813 | ~25-seat minimum; up to 5% auto-renewal increase |
| Sybill | $0 / $30 / $90 per user/mo (annual) | | 10-field autofill cap on Business |
| Oliv | $29/user/mo (annual) | | No platform fee claimed |
| Fathom | $0 / $15 / $19 / $25 per user/mo (annual) | | 2-user minimum on team plans |
| Avoma | $19 / $29 / $39 per recorder seat/mo (annual); CI and RI add-ons $29/seat | | Viewers free; Enterprise 10-seat floor |
| Pclub / Caliber | $997/user/yr | | |
| iSeeit | Per user/mo, unpublished | | Salesforce only |

### 1.5 Cross-cutting criticisms (what buyers and reps complain about)

1. Black-box scores. Gong's deal likelihood is a percentile rank routinely misread as a probability (https://prospeo.io/s/deal-health); forecast weighting is opaque ("I don't know where my weighted number comes from"). Aviso, Clari and People.ai all market "explanations" precisely because this is the objection.
2. Reps distrust and feel surveilled. G2 reviewer: reps "feel micromanaged, leading to low adoption" (Gong). Vendor-sourced framing at Oliv: "framing auto-scoring as rep enablement, not surveillance" is step one of rollout. The ooligo skill (section 4) refuses manager auto-cc for the same reason.
3. CRM hygiene dependency. Every scoring model degrades on stale CRM: Gong needs 50 won / 150 lost deals with tracked stage history; HubSpot Breeze output "depends heavily on how clean your HubSpot data is" (https://www.default.com/post/hubspot-breeze-ai-review-and-pricing); Salesforce Sales Coach "grades pitches against an empty activity log" if Activity Capture is off (https://salesforcedictionary.com/blogs/agentforce-sales-complete-2026-guide).
4. Generic methodology, not the customer's own. Gong, Avoma and Salesforce ship pre-built MEDDIC templates that are customised by adding elements; Avoma's three defaults are "non-editable". Whyte's post shows why definitions per score level matter. Clari's "upload your methodology doc" is the notable exception.
5. Keyword and embedding trackers. Gong Smart Trackers need 50-100 example sentences and operate at sentence level; teams report 8-12 hours/week filtering false positives (competitor-sourced: https://www.oliv.ai/blog/what-are-gong-smart-trackers). Gong itself shipped precision/recall assessment tools in 2024 in response.
6. Cost floor and lock-in. Platform fees, seat minimums, annual-only contracts, renewal uplifts (Gong 5-15%/yr per https://www.saasbluebook.com/tools/gong/), "wonky" APIs and data-export difficulty.
7. Silent CRM writes. RevOps warns against AI writing to production records without review; the emerging norm is propose-then-confirm (HubSpot Smart Deal Progression, Momentum Confirm-to-Write, Oliv validation workflow, Anthropic crm-maintenance skill).

---

## 2. Open-source, GitHub and community projects

### 2.1 LLM MEDDIC/MEDDPICC scoring of transcripts and deals

| Repo | What it does | Stack | Maturity |
|---|---|---|---|
| jeff266/revops-meddicc-agent | Nightly pipeline: load HubSpot deals, pull Fireflies/Gong/Apollo transcripts, Haiku context builder, Sonnet generator, Haiku evaluator and reflection gate, write back to HubSpot + Supabase; point-in-time pipeline reconstruction from property history; 28-handler Slack agent; MEDDICC/MEDDPICC/SPICED/BANT switchable in config; ~$10-20/month API cost | Python, Claude Sonnet 4.5 + Haiku 4.5, GitHub Actions, Railway | Most complete open HubSpot + MEDDICC reference found; single maintainer | https://github.com/jeff266/revops-meddicc-agent |
| jeff266/deal-intelligence-template | Prompt-only package: context builder, generator, evaluator with 7 pass/fail criteria, nightly workflow YAML, rep roll-up SQL (weakness vs team average, trends, leaderboard); "editable templates, not black boxes" | Markdown prompts, SQL | Template; no runtime code | https://github.com/jeff266/deal-intelligence-template |
| attentiontech/gtm-superintelligence | Apache-2.0; call, deal and account scoring layers; frameworks SPICED, MEDDPICC, BANT, Command of the Message, Gap Selling, Sandler as YAML; deal-health rubric (qualification coverage, multithreading, compelling event, next-step hygiene); daily rep/team/company inboxes; CRM field mappings; adapters for 9 recorders; ships as Claude Code skill + subagents + slash commands; 30 production agent templates (single-threaded detection, lost-deal post-mortems, renewals) | Python + Claude Code | Vendor-backed, best-documented; recommends Attention as recorder | https://github.com/attentiontech/gtm-superintelligence |
| zime-ai/zime-gtm-skills | MIT; 16 Agent Skills (11 stage skills + MEDDICC, BANT, pain-finder, next-step-commitment, adoption-leaderboard); "one call transcript (or CRM export) in, one evidence-cited audit out"; runs locally, no credentials; MEDDICC skill outputs per-letter Status / Evidence quote / Note and explicitly allows "Not applicable to this call"; includes EVALS.md | Markdown skills | Clean, small, honest about limits; MEDDPICC not yet built | https://github.com/Satyam97/zime-gtm-skills and https://github.com/zime-ai/zime-gtm-skills/blob/main/skills/meddicc/SKILL.md |
| violetfleming47/deal-intelligence | 6 agents (deal-tracker, conversation-scanner, blocker-scanner, lifecycle, state-builder, deal-briefer) building SCD Type 2 versioned deal state in Postgres; methodology-neutral with MEDDIC examples; harness-agnostic; full system adds weekly pattern detection and a human-confirmed hypothesis loop | Anthropic Managed Agents, Supabase | Ambitious architecture; starter subset public | https://github.com/violetfleming47/deal-intelligence |
| Dphenomenal101/playcall | Scores calls against the company's own playbook and buyer context; BYOK across 17 LLM providers; Whisper; Supabase | Next.js | Web app; small | https://github.com/Dphenomenal101/playcall |
| raven-sourav/Discovery-Call-Engine | Claude Code skill system scoring SDR and AE calls against the company's messaging files; buckets deals (Rescue/Advance/Route/Disqualify/Benchmark); "score-outcome reconciliation that compares AI scores against CRM reality"; calibration modes when a leader disagrees | Claude Code, no APIs | Notable for outcome reconciliation and calibration loops | https://github.com/raven-sourav/Discovery-Call-Engine |
| ameerbadri/call-intelligence-demo-claude-cowork | Cowork demo: 10 synthetic transcripts, per-call Intelligence Brief with MEDDPICC (8 components, identified/partially/not_addressed), SPICED 1-5, behavioural read, one subagent per transcript | Claude Cowork | Demo-grade | https://github.com/ameerbadri/call-intelligence-demo-claude-cowork |
| muruganparamasivan-automind/ai-sales-copilot | CLI + FastAPI: MEDDIC call analysis, deal scoring, next-best-action, Salesforce/HubSpot/Pipedrive clients, Whisper | Python, Claude API | Feature-broad, depth unknown | https://github.com/muruganparamasivan-automind/ai-sales-copilot |
| mephistophyles/sales-call-analyzer | Claude Skill applying Rob Snyder's PULL framework to a transcript | Markdown | Single skill | https://github.com/mephistophyles/sales-call-analyzer |
| termsheetinator/gapsi-agent | Claude Code skill: 9-section call analysis, per-deal MEDDPICC map (confirmed/partial/unknown), admissions log, persistent local memory, docx export | Markdown, local files | Solo, opinionated | https://github.com/termsheetinator/gapsi-agent |
| Divyansh-git10/FitNova-AI-Sales-Intelligence | Local-first: faster-whisper, pyannote, Ollama, SQLite; "evidence-grounded LLM scoring", evidence validator, confidence calibration, Streamlit dashboard | Python, Ollama | Release candidate; not MEDDIC-specific | https://github.com/Divyansh-git10/FitNova-AI-Sales-Intelligence |
| SaraSoleymani/gtm-ai-google-colab-notebook | LoRA fine-tune of Phi-2 to extract a proprietary "MEDDIC-R" record from transcripts, 150 synthetic pairs | Colab | Educational | https://github.com/SaraSoleymani/gtm-ai-google-colab-notebook |

### 2.2 Claude Code plugins and skill libraries for sales, RevOps and CRM

| Repo | Relevance | Notes |
|---|---|---|
| anthropics/knowledge-work-plugins (sales) | Official; skills account-research, call-prep, daily-briefing ("meetings, pipeline alerts, email priorities, suggested actions"), draft-outreach, competitive-intelligence; connectors HubSpot, Close, Fireflies, Gong, Chorus | https://github.com/anthropics/knowledge-work-plugins/tree/main/sales |
| anthropics/knowledge-work-plugins small-business/crm-maintenance | Official HubSpot skill with strict write guardrails: never delete, never change stage without approval, never auto-create deals, side-by-side diffs for cleanup | https://github.com/anthropics/knowledge-work-plugins/blob/main/small-business/skills/crm-maintenance/SKILL.md |
| anthropics/claude-tag-plugins (hubspot) | Official HubSpot v3 CRUD/search/associations skill for @Claude | https://www.claudepluginhub.com/plugins/anthropics-hubspot-hubspot |
| HubSpot/agent-cli-skills | Official HubSpot; 12 skills incl. deal-management (stalled-deal queries), sales-reporting ("daily sales briefings, pipeline snapshots, and win/loss analysis"), communication-history (pre-call briefs), crm-data-quality; dry-run/digest/confirm for writes | https://github.com/hubspot/agent-cli-skills |
| TomGranot/hubspot-admin-skills | 37 skills for audit/clean/enrich/automate HubSpot; private-app token scripts plus optional official MCP | https://github.com/TomGranot/hubspot-admin-skills |
| promptmetrics/hubspot-mcp | HubSpot MCP as a Claude Code plugin; 76 tools plus 5-tool write-safety layer (preview, approve, undo, audit log) | https://github.com/promptmetrics/hubspot-mcp/blob/main/README.md |
| cjf-iii/sales-enablement-plugin | Claude Code plugin: `/analyze-deal` MEDDIC scoring with stage gates and Deal Health Card, `/pipeline review|forecast|risk|velocity`; file-system memory; no CRM connector | https://github.com/cjf-iii/sales-enablement-plugin |
| extruct-ai/gtm-cowork-skills | Cowork/Claude Code plugin: meddpicc-post-call ("Cumulative, builds on prior scores, never overwrites higher ones"), pipeline-review, key-account-plan; Attio + Granola + Gmail | https://github.com/extruct-ai/gtm-cowork-skills |
| yeutterg/claude-code-sales-skills | Obsidian-based SE workflow: Gong import via Playwright, MEDDPICC tracking, `/sales-today` daily and `/sales-weekly` review with Salesforce push | https://github.com/yeutterg/claude-code-sales-skills |
| jpeslar1/linkedin-mcp-ae-daily-briefing | 7:30am Claude Code briefing: Pipedrive + calendar + LinkedIn signals to Slack DM | https://github.com/jpeslar1/linkedin-mcp-ae-daily-briefing |
| LeadMagic/gtm-skills | 205 GTM skills incl. pipeline-management, meeting-prep, hubspot-setup | https://github.com/LeadMagic/gtm-skills |
| TheCraigHewitt/skills (sales) | 21 skills; pipeline-review skill has a risk-flag table (no next step, single-threaded, ghost champion, close date pushed 2+) and zombie-deal rules | https://github.com/TheCraigHewitt/skills/blob/HEAD/sales/pipeline-review/SKILL.md |
| Doris-Labs/sales-skills | meddpicc-qualification, deal-risk-review, forecast-hygiene, crm-hygiene; three tiers of tool binding | https://github.com/Doris-Labs/sales-skills/blob/main/README.md |
| jmbluhm/b2b-sales-skills | 27 methodology skills (MEDDPICC, multi-threading) citing Gong Labs stats | https://github.com/jmbluhm/b2b-sales-skills |
| sales-skills/sales | Router skill over hundreds of platform skills (Gong, HubSpot, Attention, Fathom...) with pricing notes | https://github.com/sales-skills/sales |
| Revenoid-Inc/revenoid-claude-plugin | 26 tools incl. search_call_transcripts (Gong/Chorus/Avoma), crm_query, pre-call-prep | https://github.com/Revenoid-Inc/revenoid-claude-plugin |
| jeremylongshore hubspot-pack | 10 engineering skills incl. deal-pipeline-automation (stale-deal safe-close, forecast reconciliation) | https://github.com/jeremylongshore/claude-code-plugins-plus-skills/blob/main/plugins/saas-packs/hubspot-pack/skills/hubspot-deal-pipeline-automation/SKILL.md |
| matellez/claude-skills | hubspot-audit, pipeline-health-reviewer, win-loss-analysis | https://github.com/matellez/claude-skills |
| ooligo skills | activity-summarizer (Friday rep self-review, rep-first privacy) and ae-rep-coaching (three/two/one note with transcript citations, no score without citation, escalation gate) | https://ooligo.com/en/workflows/activity-summarizer-skill/ and https://ooligo.com/en/workflows/ae-rep-coaching-skill/ |
| Curated lists | matteotitta/awesome-claude-code-for-gtm (notes `HubSpot/mcp-server` on GitHub is an empty placeholder); sujayjayjay/awesome-sales-automation-skills; ComposioHQ/awesome-claude-skills | https://github.com/matteotitta/awesome-claude-code-for-gtm , https://github.com/sujayjayjay/awesome-sales-automation-skills , https://github.com/ComposioHQ/awesome-claude-skills |
| AI Builder Club catalogue | 60+ sales skills across 12 repos, June 2026 | https://www.aibuilderclub.com/blog/claude-code-for-sales-skills-guide |

### 2.3 HubSpot MCP servers

| Server | Coverage | Notes |
|---|---|---|
| Official remote (mcp.hubspot.com) | Read/write CRM objects and engagements (calls, emails, meetings, notes, tasks); OAuth 2.0 moving to 2.1 with PKCE; no sensitive-data properties | https://developers.hubspot.com/ai-tools/mcp |
| ohneben/Hubspot-MCP | 1,076 endpoint tools from HubSpot OpenAPI, safety categories, hub/plan awareness, read-only mode, GraphQL passthrough | https://github.com/ohneben/Hubspot-MCP |
| nubiia-dev/mcp-hubspot | 56-72 tools, engagements logging, workflows v4 | https://github.com/nubiia-dev/mcp-hubspot |
| axonops/hubspot-mcp | 76 tools, per-user OAuth, marketing-heavy | https://github.com/axonops/hubspot-mcp |
| shinzo-labs/hubspot-mcp | Broad CRM + engagement_details_* tools | https://github.com/shinzo-labs/hubspot-mcp |
| baryhuang/mcp-hubspot | Early (Dec 2024), FAISS cache, conversations | https://github.com/baryhuang/mcp-hubspot |
| SanketSKasar/HubSpot-MCP-Server | HTTP/SSE/stdio wrapper with get_engagement_history | https://github.com/SanketSKasar/HubSpot-MCP-Server |

### 2.4 Engineering patterns worth copying (from the docs and repos above)

Field extraction and scoring:
- Silence rule. Momentum's prompt guidance: "Silence = output nothing", "Extract from explicit mentions only. Do not infer", "No over-extraction (inferring content not in the transcript)". Picklists must return an exact allowed value; dates must be YYYY-MM-DD and never inferred. https://docs.momentum.io/ai-prompting-autopilot
- Per-stage applicability. Zime's MEDDICC skill scores "whatever letters that specific call could plausibly have surfaced" and returns "Not applicable to this call" rather than "Missed", because "a MEDDICC read that penalizes every call for not being the final negotiation call is not useful". https://github.com/zime-ai/zime-gtm-skills/blob/main/skills/meddicc/SKILL.md
- Cumulative deal state with carry-forward. jeff266 builds deal-level state from per-call scores with a Haiku "context builder" rather than re-reading full history; Oliv describes a score moving from 1 to 3 on Economic Buyer as later calls add evidence, with each change linked to the triggering moment; extruct's skill "never overwrites higher" scores. https://github.com/jeff266/revops-meddicc-agent , https://oliv.ai/blog/meddic-auto-scoring-sales-methodology-enforcement , https://github.com/extruct-ai/gtm-cowork-skills
- Evaluator gate before any CRM write. jeff266's three-role pipeline (context builder, generator, evaluator) with 7 pass/fail criteria, plus a reflection gate; failed analyses never touch the CRM. https://github.com/jeff266/deal-intelligence-template
- Score-level definitions to remove optimism variance. Whyte: confidence scores varied by personality until each level got a written definition; then stage gates (Decision Process >= 8/10 to enter Negotiation) became enforceable. https://meddicc.medium.com/lessons-learned-from-implementing-meddpiccr-a-year-on-25cafef1330b
- Calibration loop against humans. Oliv recommends a 2-week parallel run comparing auto-scores with manager scores on 10-15 deals; Discovery-Call-Engine has explicit "leader disagrees with score" modes that rewrite the rules; Stratyfix "calibration switches on at your 200th scored conversation". https://oliv.ai/blog/meddic-auto-scoring-sales-methodology-enforcement , https://github.com/raven-sourav/Discovery-Call-Engine , https://stratyfix.com/
- Outcome reconciliation. Discovery-Call-Engine mode 8 reconciles AI scores against CRM outcomes; ooligo's success criteria define precision targets such as "Cooling flags a deal that subsequently goes Closed Lost >= 70% of the time". https://github.com/raven-sourav/Discovery-Call-Engine , https://ooligo.com/en/workflows/activity-summarizer-skill/

Write safety and trust:
- Staged trust. Momentum: Confirm-to-Write for weeks 1-2, Write-if-Empty as the standing default, Automatic only for validated high-confidence fields. HubSpot Smart Deal Progression and Anthropic's crm-maintenance skill are approve-per-suggestion by design. promptmetrics/hubspot-mcp wraps every write in preview, approve, undo and audit log. https://docs.momentum.io/autopilot-classic-setup , https://github.com/promptmetrics/hubspot-mcp/blob/main/README.md
- Hard refusals. crm-maintenance: never delete, never change stage or close a deal without explicit approval, never create a deal unprompted, announce contact creation before writing. HubSpot agent-cli-skills: dry-run, digest, confirm for destructive operations, `hubspot history` for recovery. https://github.com/anthropics/knowledge-work-plugins/blob/main/small-business/skills/crm-maintenance/SKILL.md , https://github.com/hubspot/agent-cli-skills
- Rep-first delivery. ooligo hard-codes DM delivery and rejects manager channel IDs; ae-rep-coaching verifies manager-of-record before reading any transcript and has an escalation gate that refuses to produce a coaching note when a criterion (pricing misrepresentation, hostile tone) fires. https://ooligo.com/en/workflows/ae-rep-coaching-skill/
- Context isolation for large transcript volumes. The Cowork demo never reads transcripts in the parent conversation; one subagent per transcript, up to five in parallel, context discarded after the brief is written. https://github.com/ameerbadri/call-intelligence-demo-claude-cowork

Data plumbing:
- Transcript sources and timing metadata differ: Fireflies gives seconds, Apollo milliseconds, Gong's API gives no talk-time data; Gong indexes calls by email not CRM user ID; drop "Logged Email" tasks with empty bodies as hygiene noise. https://github.com/jeff266/revops-meddicc-agent , https://ooligo.com/en/workflows/activity-summarizer-skill/
- Point-in-time pipeline reconstruction from HubSpot property history is needed to ask "what did the pipeline look like on date X", otherwise current state is projected backward. https://github.com/jeff266/revops-meddicc-agent
- HubSpot reporting caches stage aggregates for up to 4 hours; query the CRM search API directly for live quota views; four distinct amount fields on a deal can disagree. https://github.com/jeremylongshore/claude-code-plugins-plus-skills/blob/main/plugins/saas-packs/hubspot-pack/skills/hubspot-deal-pipeline-automation/SKILL.md
- HubSpot CRM v3 and automation v4 REST are supported until March 30, 2027; the date-based 2026-03 release is the recommended target. https://github.com/TomGranot/hubspot-admin-skills

### 2.5 Maturity assessment

- Scoring a transcript against MEDDPICC with quoted evidence is a solved, commoditised prompt. Zime, gtm-superintelligence, jeff266 and the Cowork demo all do it; the quality differentiator is now (a) per-stage "not applicable" logic, (b) cumulative deal-level state across calls, (c) an evaluator gate before writing, and (d) a calibration loop when a human disagrees. jeff266 and Discovery-Call-Engine have (b)-(d); Zime has (a).
- None of the open projects produce a team-level *adoption* report over time, and only Discovery-Call-Engine (mode 8, "reconcile scores vs reality") and jeff266's rep roll-up SQL attempt any score-to-outcome comparison. gtm-superintelligence's deal-health rubric estimates win-likelihood but does not back-test it.
- None do deterministic quote verification (the Stratyfix pattern). "Evidence-bound" in these repos means the LLM was asked to quote.
- The HubSpot read path is well served: official remote MCP, official Agent CLI with skills, and several community MCPs with write-safety layers (promptmetrics). Reading call transcripts from HubSpot depends on Notetaker/Conversation Intelligence being enabled (Sales Hub Pro/Enterprise) or on a connected recorder; every open project instead pulls transcripts from Gong/Fireflies/Apollo/Granola.
- The Anthropic-official pattern (crm-maintenance, Cowork case study, HubSpot agent-cli-skills) is propose-then-confirm with read-first trust building. A plugin that writes silently would be out of step with both the official guidance and RevOps sentiment.

---

## 3. Measuring sales-training ROI

### 3.1 State of practice

- Kirkpatrick's four levels (Reaction, Learning, Behavior, Results; Donald Kirkpatrick, 1959) remain the default frame; Phillips adds a fifth level, ROI. https://www.devlinpeck.com/content/kirkpatrick-model . One practitioner guide asserts "Fewer than 20% consistently measure Level 3, and under 10% reach Level 4" (no source given). https://prospeo.io/s/sales-training-kpis . Bigtincan and Everstage publish Kirkpatrick-for-enablement templates. https://www.bigtincan.com/resources/securing-sales-enablement-buy-in-applying-the-kirkpatrick-model-to-enablement-maturity/ , https://www.everstage.com/sales-effectiveness/how-to-measure-sales-training-effectiveness
- Completion and attendance still dominate. SBI + Revenue Enablement Society benchmark (Feb 2025, 134 companies): the five most-used effectiveness metrics are quota attainment 78%, sales KPIs 77%, training completion rates 74%, revenue growth 73%, win rate 73%; "teams struggle most with measuring the impact of enablement". https://index.sbigrowth.com/hubfs/Modern%20Enablement%20Benchmarks%20Report%20-%20February%202025.pdf
- D2L 2023 (cited by Sandler): 61% believe their learning programs are effective, only 33% formally assess financial outcomes or ROI. https://sandler.com/blog/sales-training-works-heres-why-you-cant-prove-it/
- Vantage Point + Sales Management Association 2016 (213 companies, 200,000 salespeople): companies that measured sales-management training effectiveness had 13% greater revenue-target achievement and 19% greater profit-goal achievement than those that did not. https://www.td.org/insights/measure-trainings-impactor-suffer-the-consequences
- Practitioner frameworks converge on a three-tier model: activity (completion, attendance), capability (assessment lift, call-quality scores from conversation intelligence, manager coaching ratings), business impact (win rate, cycle, ramp). https://www.salesassembly.com/blog/revenue-leadership/how-to-measure-sales-enablement-roi/ . The "leading vs lagging" framing: leading = behaviour change on calls, lagging = quota and win rate, with a 90+ day lag and an attribution problem ("Did quota improve because of training, or pipeline, or market?"). https://vozah.com/blog/measure-training-effectiveness
- Vendor benchmark reports that get quoted: Highspot 2025 (AI coaching users "36% more likely to report higher win rates"; managers spend 13 hrs/week coaching) https://www.highspot.com/state-of-sales-enablement-2025/ ; Mindtickle 2025 (top-24 orgs do 6x more role-plays; Digital Sales Rooms +26% win rate) https://campaigns.mindtickle.com/2025-state-of-revenue-enablement-report/ ; Allego/LXA 2025 (effectiveness measured by productivity KPIs 51%, ROI 47%, churn 44%) https://hs-4668355.f.hubspotemail.net/hubfs/4668355/03_Content/State%20of%20Sales%20Enablement%202025%20(Allego)/State%20of%20Sales%20Enablement%20Report%20-%20Final.pdf
- Ambition's pitch is exactly the gap: "Did your latest MEDDPICC certification increase qualified pipeline?" requires joining LMS completion data (Highspot, Mindtickle) with CRM outcomes, which most teams cannot do. https://ambition.com/blog/how-to-measure-the-roi-of-sales-enablement-with-ambition

### 3.2 The zombie statistics, traced

| Statistic | Usual attribution | What the trail shows |
|---|---|---|
| "87% of sales training is forgotten within 30 days" | Xerox, or Neil Rackham, or Huthwaite | First published in the ASTD Journal, Nov 1979, as a Huthwaite/Xerox study of *skill* loss after training in the absence of coaching; Rackham's *Managing Major Sales* (1991), fig 5.1 p.130: "Sales training without systematic coaching wastes 87 cents in the dollar", and p.129 notes reps who were coached showed a skills *gain*; Rackham's 2001 "The Coaching Controversy" quotes it as "in the absence of follow-up coaching 87 per cent of the skills change... was lost". The Challenger Sale then restated it as content "forgotten within thirty days". The underlying Xerox Newcastle branch story (35 reps, 16th of 17 to 1st after six months of on-the-job coaching, calls per order halved) is the original evidence. Sources: http://brianmaciver.blogspot.com/2011/11/is-it-true-that-87-cents-of-every.html , https://img1.wsimg.com/blobby/go/2f31b598-e348-46d0-8061-05e66ffa837e/Importance%20of%20Follow%20Up.pdf , https://now.iseeit.com/on-the-job-coaching-can-transform-sales-performance/ . Verdict: a real but 45-year-old finding about *skills without coaching*, not about knowledge decay in 30 days. |
| "Reps forget 50% in 5 weeks and 84% in 90 days" | Sales Performance International | Circulates verbatim in SBI (2012), Training Industry (2017), Integrity Solutions, Sitkins and Closing Foundry copy; no primary SPI document is ever linked. https://sbigrowth.com/insights/blog/why-sales-training-fails , https://trainingindustry.com/content/uploads/2017/07/training-effectiveness-whitepaper.pdf . Salesprep's write-up calls the 84-87% family "a zombie stat: it survives because it sounds right, not because anyone measured it." https://salesprep.ai/blog/forgetting-curve-sales-training . Verdict: unsourced. |
| "85-90% of sales training has no lasting impact after 120 days" | ES Research Group | Dave Stein, *Sales Training: The 120-Day Curse* (ES Research Group, 2011), a paid analyst report cited by RAIN Group and others; the report is not public. https://whitepapers.lakewoodmediagroup.net/sites/default/files/Why%20Sales%20Training%20Fails.pdf , https://pleinairestrategies.com/2017/01/four-reasons-why-companies-waste-90-of-sales-training-dollars/ . Verdict: real report, unknown method, analyst estimate rather than a measured study. |
| The forgetting curve itself | Ebbinghaus 1885 | Replicated by Murre and Dros, PLOS ONE 2015; the shape (steep early loss, then a plateau) is robust; specific percentages are popularisations. https://salesprep.ai/blog/forgetting-curve-sales-training |

### 3.3 Rigorous and semi-rigorous evidence on training, coaching and methodology effects

Randomised or quasi-experimental:
- Sandvik, Saouma, Seegert and Stanton, NBER w26660 (published as "Workplace Knowledge Flows", QJE): field experiment with 653 sales agents; structured peer meetings about sales techniques raised revenue-per-call 24% during the four-week intervention and remained 18-21% higher twenty weeks later; pair incentives alone produced only transitory gains. https://www.nber.org/system/files/working_papers/w26660/w26660.pdf
- Same authors, NBER w29148: RCT of formal mentorship in an inbound sales call centre; mentored new hires produced ~18-19% more revenue in their first months, effects persisting through six months; among agents who opted in, the treatment effect was negligible, so voluntary programmes reach the wrong people. https://www.nber.org/system/files/working_papers/w29148/revisions/w29148.rev0.pdf
- Gignac et al. 2012: experimental design, 50 pharmaceutical reps; emotional-intelligence training group outperformed controls by ~9% in sales performance. Reported in a 30-year review (56 papers, 1985-2014) that found only two experimental studies in the whole sales-training literature. https://www.sciencedirect.com/science/article/pii/S2077188615000025
- Kauffeld and Lehmann-Willenbrock 2010: spaced rather than massed sales training produced greater transfer and improved performance figures (same review).
- Sarin, Sego, Kohli and Challagalla 2010 (JPSSM): formality of training raised, voluntariness lowered, perceived training effectiveness during a sales-strategy change. https://doi.org/10.2753/pss0885-3134300205
- Activity-based incentives, JMR 2021: three-year treatment-removal field intervention across 305 pharma territories with synthetic controls; ABI pay produced 6-9% sales gains. https://journals.sagepub.com/doi/10.1177/00222437211020013
- Honeycutt et al. 2001 propose a utility-analysis framework for the financial evaluation of sales training, noting "limited attention has been devoted to the financial evaluation of sales training programs". https://doi.org/10.1080/08853134.2001.10754274
- Longitudinal SFA adoption study (156 salespeople, before and six months after): training, customer pressure and peer use drive adoption, and adoption enhances performance. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1582980

Correlational, but with decent samples:
- Vantage Point + Sales Management Association (2013-14, 62 B2B companies): a formal sales process with defined exit criteria correlated with ~18% higher year-over-year revenue growth; spending 3+ hours per month per rep on pipeline coaching correlated with 11% greater growth; training managers on pipeline management ~10%; all three together 28%. https://salesandmarketing.com/coaching-winning-game-plan-pipeline-management/ and https://cdn2.hubspot.net/hubfs/2689550/Documents/Articles%20&%20White%20Papers/Pipeline/3%20Secrets%20of%20Successful%20Pipeline%20Management%20-Insight%20Squared.pdf
- CSO Insights 5th Annual Sales Enablement Study (Miller Heiman Group, 2019): the only published table relating *methodology adoption rate* to outcomes. Adoption <75% of the sales force: quota attainment 49.4%, win rate 40.4%; 75-90%: 64.0% and 54.1%; >90%: 72.4% and 57.8% (study averages 60.0% and 46.4%). Dynamic coaching: 55.2% win rate vs 41.8% for random. https://community.highspot.com/wp-content/uploads/2019/10/CSO-Insights-5th-Annual-Sales-Enablement-Study.pdf . Korn Ferry's 2023 restatement: dynamic sales process yields 21% higher quota attainment and 26% higher win rates. https://www.kornferry.com/insights/featured-topics/sales-transformation/growing-sales-pipeline-during-times-of-change
- Aberdeen 2010 (835 organisations, Sandler-sponsored analyst insight): best-in-class 93% team quota attainment vs 59% average; post-training reinforcement adopted by 54% of best-in-class vs 28% of laggards; integrating training content with CRM stage flags adopted 83% more often by best-in-class. https://21604003.fs1.hubspotusercontent-na1.net/hubfs/21604003/Franchise%20Development%20Marketing/Aberdeen%20Sandler%20ROI.pdf
- Sandler Research Center / Sales Mastery 2022 (Trailer and Dickie): 68% of orgs coach ad hoc; orgs with ongoing training plus formal coaching reported 100% revenue attainment and 73% of reps at quota; shared buyer-process understanding 51% vs 27% conversion. https://sandler.com/blog/leading-uncertain-times-sales-mastery-analysis/
- Ebsta's three benchmark reports (section 1.2) are the largest deal-level datasets relating MEDDPICC completion to win rate, but they are cross-sectional and stage-confounded (deals that progress further accumulate more fields).
- Gong Labs: 1.8M opportunities, won deals have 2x buyer contacts, 130% win-rate lift from multi-threading on $50K+ deals. Gong itself warns "Correlation and causation aren't the same things" in its 519,000-call discovery study. https://www.gong.io/blog/the-best-sales-insights-of-2025 and https://www.gong.io/blog/nailing-your-sales-discovery-calls

Weak but often quoted:
- Teplitz "Switched-On Selling": self-assessment pre/post plus a South Carolina Farm Bureau two-group comparison claiming +39% sales; no randomisation, vendor-run. https://teplitz.com/PDF/XSOS%20Research%20Report.pdf

Evidence-quality ladder, strongest to weakest, for anything Flow Sales might cite:
1. Randomised field experiments in sales settings: NBER w26660 (structured peer meetings), NBER w29148 (mentorship), Gignac 2012 (EI training). None concern MEDDIC or any qualification methodology.
2. Quasi-experimental with controls: JMR 2021 activity-based incentives (synthetic control); Rackham's Xerox Newcastle branch (before/after on one branch, no control).
3. Large-sample correlational with outcome data: Ebsta 2023-2025 (millions of opportunities; stage-confounded), Gong Labs (1.8M opportunities; multithreading), UserGems and Champify (thousands of opportunities; champion job changes).
4. Survey-based correlational: CSO Insights 2019 (adoption bands vs win rate), Vantage Point/SMA 2013-14 and 2016, Aberdeen 2010, Sales Mastery 2022.
5. Single-customer vendor cases: People.ai Red Hat, MEDDICC.com PE case, Force Management, Sandler, Flow State, Nooks.
6. Analyst estimates and folklore: ES Research 85-90%, "87% in 30 days", "84% in 90 days".

Bottom line: there is no published before/after study in which methodology adoption was measured at the conversation level (did the rep actually ask for the economic buyer, quantify pain, confirm the paper process) and then linked to revenue with controls. Vendor datasets measure field completion, not conversational behaviour, and consultancies measure business outcomes without adoption instrumentation.

### 3.4 How training consultancies present ROI today

Force Management (Command of the Message + MEDDPICC; Opportunity Manager Salesforce plug-in; Ascender e-learning)
- Patra: after one year, win rate +143%, days to close -32%, average deal size +48%, bookings per person +32%; "lower push rate... primarily from using and applying the rigor of MEDDPICC". https://www.forcemanagement.com/patra-case-study
- Aptean: 64% larger new-logo deals, 15-point drop in loss percentage, "95% of Managers report improved deal reviews", 400+ trained. https://www.forcemanagement.com/aptean-case-study
- project44: +53% average deal size, cycle -19%, 115% YoY ARR growth over two quarters. https://www.forcemanagement.com/project44-case-study
- Intercom: average deal size +261%, reinforced by Troops Slack prompts that walk reps through Command of the Message and MEDDPICC fields after every call. https://www.forcemanagement.com/intercom-case-study
- RSA (deals $250-500K up 30% in the first quarter) and Firstup (4x large-deal pipeline). https://www.forcemanagement.com/rsa-case-study , https://www.forcemanagement.com/firstup-case-study
- Pattern: year-over-year business metrics, occasionally a manager survey; no adoption metric other than "trained/certified" counts.

Winning by Design (Revenue Architecture, SPICED, Bowtie)
- Aggregate, unattributed: "50% decrease in length of sales cycle, 298% increase in wins, 3x ARR year over year, 8x outbound pipeline share". https://winningbydesign.com/revenue-architecture/ and https://winningbydesign.com/spiced-framework/ (25K+ trained on SPICED)
- Customer stories (Canva, Lambda, OneStream) are qualitative; OneStream cites $110.3M quarterly revenue pre-IPO. https://winningbydesign.com/customers/canva/ , https://winningbydesign.com/customers/lambda/ , https://winningbydesign.com/customers/onestream/
- 2026 Impact Summit awards: "SPICED adoption at scale reduces late-stage deal loss and improves forecast accuracy"; "1,500 sellers, 20 CRM systems, one qualification standard". https://winningbydesign.com/resources/research/stories-of-gtm-innovation/

Sandler
- HubSpot: 15% sales productivity, 18% shorter closing cycle, 12% higher ASP after 16 months; Sandler "identified the critical leading metrics (activities) that correlated with the lagging metrics of revenue". https://enterprise.sandler.com/hubfs/Sandler-HubSpot-Case-Study.pdf
- SAP Concur: 30% reduction in deal time in targeted cohorts; 12.75% annual deal-size and 9.75% annual win-rate improvement over five years; KPIs used to pick middle performers for cohorts. https://sandler.com/case-study/driving-global-sales-alignment-and-performance-at-sap-concur-with-sandler/
- Symantec: push-out fell from 12% of deals (30-35% of revenue). https://sandler.com/case-study/symantec/
- June 2026 position paper "Sales Training Works. Here's Why You Can't Prove It": the industry has "never been a way to make that return both measurable and actionable"; Sandler now claims conversational-intelligence analytics that "confirm seller skill adoption and establish a clear connection between the skills learned during sales training and revenue outcomes" via its proprietary Sales Performance Ecosystem. https://sandler.com/blog/sales-training-works-heres-why-you-cant-prove-it/

MEDDICC.com
- PE-backed customer: forecast accuracy 25% to 85%, win rate 23% to 46%, quota attainment 44% to 83%, ACV $50k to $81k in 24 months. https://meddicc.com/customer-stories/m1
- Anecdotes: a customer's enterprise ACV +240% after one quarter; internally promoted SDRs hit 120% attainment vs 80% for external AE hires. https://www.youtube.com/watch?v=GyYVq4UsE3I , https://meddicc.com/meddicc-media/medmen-s1-ep2-sales-development-representatives

Flow State Sales (London, founded 2020, 4 people, MEDDIC/MEDDPICC embedding is a core service)
- Metomic: win rate "from the low 20s to 50%", deal size doubled. https://flowstatesales.com/case-studies/metomic/
- Fastmarkets: cross-sell revenue +147%, AOV +24%, churn 11% to 6.4%, forecast accuracy +14%, MEDDIC-based qualification framework built in workshops. https://flowstatesales.com/case-studies/fastmarkets-increased-cross-sell-revenue/
- MEDDIC module page: "78% increase in MRR, 44% increase in AOV, 25% better revenue forecasts"; "bigger results, like higher win rates or deal sizes, tend to show up over 1-2 quarters". https://flowstatesales.com/flow-state-training-modules/meddic-sales-team-training-and-deal-coaching/
- SAE Media Group rebookings +300%; index of 20+ case studies. https://flowstatesales.com/case-studies/ , https://linkedin.com/company/flow-state-sales-performance-transformation

Pattern across all five: outcome deltas with no control group, no adoption measurement, and no separation of training effect from hiring, ICP change or market. Sandler is the only one now explicitly promising an instrumented link, and it is proprietary.

---

## 4. Concrete "great use case" examples of AI agents on CRM data

Outcome-evidence key: (V) vendor or customer self-reported number; (T) time-saved self-report; (C) correlational research; (N) none published.

| # | Use case | Who / where | One-line description | Evidence |
|---|---|---|---|---|
| 1 | Daily call prep + Friday forecast + overnight territory scoring | Anthropic, Travis Bryant, Claude Cowork on Salesforce + BigQuery | Scheduled skill briefs each day's meetings; Friday skill assembles a leadership-format forecast page; 4,000 accounts scored overnight with a written rationale per dimension and an interactive dashboard; humans approve every send. https://claude.com/blog/how-an-anthropic-sales-leader-uses-claude-cowork-to-run-a-4-000-account-book | (T) ~90 min/day, ~3 hrs/week |
| 2 | Daily briefing skill | anthropics/knowledge-work-plugins `sales/daily-briefing` | "Prioritized daily sales briefing: meetings, pipeline alerts, email priorities, suggested actions" with HubSpot/Gong/Fireflies connectors. https://github.com/anthropics/knowledge-work-plugins/tree/main/sales | (N) |
| 3 | Propose-only CRM maintenance | anthropics `crm-maintenance` | Resolves contact and deal from an email or calendar event, logs activity, shows current-vs-proposed diffs, never changes stage or deletes without approval. https://github.com/anthropics/knowledge-work-plugins/blob/main/small-business/skills/crm-maintenance/SKILL.md | (N) |
| 4 | Stale-deal hunt and daily briefings from the CLI | HubSpot/agent-cli-skills `deal-management`, `sales-reporting` | `hubspot objects search --filter "hs_last_activity_date<... AND hs_is_closed!=true"` piped into task creation; dry-run/digest/confirm on writes. https://github.com/hubspot/agent-cli-skills/blob/HEAD/deal-management/SKILL.md | (N) |
| 5 | Morning Brief, Sunset Summary, Weekly Forecast one-pager | Oliv Deal Driver and Forecaster agents | Pre-call brief 30 min before each meeting; evening list of deals won/moved/at risk; Monday line-by-line deal inspection with risk commentary and a slide deck; Evidence Logs. https://www.oliv.ai/blog/oliv-ai-features-platform-guide-head-of-sales | (V) unverified |
| 6 | Deal risk alerts with methodology gaps in the pipeline view | Salesforce Pipeline Inspection | Alerts column for single-threaded contacts, pushed deals and activity drops, next to out-of-the-box MEDDIC/MEDDPICC gap indicators; one-click field updates. https://www.salesforce.com/sales/latest-release/ | (N) |
| 7 | Methodology playbook on the deal board | Gong AI Deal Reviewer | Colour-coded MEDDICC letters per deal, AI-suggested notes the AE validates, "who's following process" at a glance. https://help.gong.io/docs/understanding-ai-deal-reviewer | (C) Gong Labs multithreading data, not adoption data |
| 8 | Daily methodology compliance inspection | Clari Deal Inspection Agent | Evaluates every targeted opportunity daily against per-stage criteria generated from the uploaded methodology doc, using CRM fields plus transcripts and emails. https://community.clari.com/ai-chatgpt-and-revai-83/configuring-the-ai-deal-inspection-agent-2871 | (N) |
| 9 | MEDDPICC scorecards with real-time risk surfacing | People.ai/Backstory at Red Hat | AI flags missing economic buyers and engagement gaps on live deals so managers coach in flight. https://www.backstory.ai/case-studies/red-hat | (V) 50%+ win-rate lift on deals with >=70% completion |
| 10 | Champion job-change detection | UserGems, Champify | Alerts and new contact records when past buyers or champions move; outreach to alumni. https://www.usergems.com/blog/how-much-are-previous-champions-worth , https://www.champify.io/resources/the-impact-of-tracking-job-changes-value-report | (V) UserGems: 114% higher win rate, 54% larger deals over 5,000 opps; Champify: 37% vs 19% win rate, 6.3x conversion efficiency |
| 11 | Stuck-in-stage and field-validation nudges in Slack | Rattle | Alerts when an opportunity exceeds expected time in stage; CRM Data Agent proposes field values with reasoning; deal rooms. https://help.gorattle.com/en/articles/5671362-using-create-update-workflows | (V) testimonial "30% more accurate forecasting" |
| 12 | Confirm-to-write MEDDPICC field extraction | Momentum Autopilot | Per-call, event-triggered and batch extraction into Salesforce with explicit silence rules and staged trust (confirm, write-if-empty, automatic). https://docs.momentum.io/ai-prompting-autopilot | (V) Ramp: "cut the time in half" |
| 13 | Single-threaded detection, lost-deal post-mortems, renewal watch | Attention's 30 open agent templates in gtm-superintelligence | Post-call agents that "flag at-risk deals, catch single-threaded deals, run lost-deal post-mortems, watch renewals, and prep handoffs". https://github.com/attentiontech/gtm-superintelligence | (N) |
| 14 | Weekly coaching email with source links | Salesloft Sales Strategist Agent | Every Monday: impact last week, focus areas, strengths; each "area for improvement" links to the specific deal, call or email it was based on; creates Rhythm tasks; runs on a fixed weekly schedule. https://help.salesloft.com/s/article/Sales-Strategist-Agent-for-Reps-and-Sellers | (N) |
| 15 | Friday rep self-review, rep-first privacy | ooligo activity-summarizer skill | Six bullets (three heating, two stuck, one named suggestion) from Salesforce + Gong; manager auto-cc deliberately non-configurable "or reps start gaming the input data within a week"; success criteria such as "Cooling bucket flags a deal that subsequently goes Closed Lost >= 70% of the time". https://ooligo.com/en/workflows/activity-summarizer-skill/ | (N) |
| 16 | Coaching note that cites the call | ooligo ae-rep-coaching; Airspeed; Avoma; Halo; Stratyfix | "No score without a citation"; three-working / two-tighten / one-exercise; Airspeed: "prospect mentioned budget constraints at 14:32 and rep moved to demo at 14:45 without following up"; Stratyfix verifies quotes deterministically. https://ooligo.com/en/workflows/ae-rep-coaching-skill/ , https://www.goairspeed.com/blog/how-ai-finds-coaching-moments-in-sales-calls , https://stratyfix.com/ | (V) Airspeed 40% faster ramp |
| 17 | Post-call CRM suggestions, follow-up draft, next steps | HubSpot Smart Deal Progression | Triggered after every recorded call; rep approves each suggested property change. https://www.hubspot.com/products/sales/smart-deal-progression | (N) |
| 18 | Weekly at-risk email from a methodology score | Meddicc Score for HubSpot | "Your team will receive weekly emails highlighting deals at risk and what information is missing"; average score per rep and trend reports. https://meddiccscore.com/hubspot/ | (N) |
| 19 | Weekly "Deal Team" review on MEDDPICC in HubSpot | Ebsta at Cappy | Reps qualify in-CRM, leaders review MEDDPICC and relationship scores weekly. https://www.ebsta.com/case-study/cappy/ | (V) qualitative adoption increase |
| 20 | Coaching-quality BDR floor with AI roleplay and scoring | Nooks at HubSpot | Golden Hour virtual sales floor, AI scorecards, roleplay before first dial. https://www.nooks.ai/customer-success/hubspot | (V) 24% pipeline-per-BDR, ramp 6 to 4 months |
| 21 | Warning-trigger thresholds scaled to cycle length | Weflow | No activity 7/14/21 days and ghosted 4/7/14 days depending on sales-cycle length; close date pushed; methodology fields empty. https://www.weflow.ai/blog/deal-health-signals-framework | (N) |
| 22 | Morning briefing from LinkedIn signals + pipeline | jpeslar1 Claude Code prompt | 7:30am, three bullets per meeting to Slack DM, on the argument that Gong/Clari/HubSpot briefings ship stale prospect data. https://github.com/jpeslar1/linkedin-mcp-ae-daily-briefing | (N) |
| 23 | Proactive seller guidance from existing models | Salesforce internal (Data Cloud + Slack + Sales Coach) | Personalised, action-driven guidance pushed to sellers rather than dashboards. https://www.salesforce.com/blog/ai-sales-enablement/ | (V) "$37M in combined pipeline and revenue" |

Observations for design:
- The strongest outcome evidence in the whole set is for champion job-change tracking and MEDDPICC completion, both correlational and vendor-reported.
- Every credible briefing pattern is scheduled (cron), rep-facing first, and short (three to six bullets). Every credible coaching pattern cites a timestamp and quote.
- The propose-then-confirm write model is now the norm across Anthropic, HubSpot, Momentum, Oliv and Rattle.
- Nobody publishes a *weekly retro* for reps that reports methodology adoption per element against their own prior weeks; Salesloft and ooligo come closest (weekly, sourced), but on activity and call quality, not on framework coverage.

---

## 5. Differentiation notes

Gaps a transparent, local-first, evidence-quoting, framework-adoption-measuring open plugin could own:

1. Adoption as a trajectory, not a snapshot. Gong shows "how much your team is applying your methodology overall" inside a paid Forecast seat; Ebsta and CSO Insights publish adoption benchmarks as PDFs; Oliv reports "methodology coverage by rep" weekly. Nobody produces, from the customer's own HubSpot, a per-rep, per-element, per-stage adoption curve over time, with cohorts before and after a training date. That is the artefact a sales leader and a training consultancy both lack, and it is what Kirkpatrick Level 3 (behaviour) actually requires.

2. Adoption-to-outcome correlation on the customer's own pipeline. Ebsta's 6.3x and People.ai's Red Hat 50% are aggregate or single-case vendor numbers. A plugin that computes win rate, cycle time and slippage by MEDDPICC coverage band, by element, with stage and deal-size controls and an explicit survivorship caveat, gives every team its own Ebsta report, reproducibly, from open code. It also gives consultancies (Force Management, Sandler, Flow State, MEDDICC.com) the instrumented proof they currently cannot show; Sandler's 2026 paper concedes this and locks the answer inside a proprietary ecosystem.

3. Evidence that is verified, not just requested. Almost every tool says "evidence-based"; only Stratyfix runs a deterministic check that the quoted line exists in the transcript and refuses to ship the score otherwise. No open-source project does this. Quote-verified, versioned, per-element scores are the direct answer to the two loudest complaints in section 1.3 (black-box scores, rep distrust).

4. The customer's methodology, as a file they own. Vendors ship generic MEDDIC templates (Avoma's are non-editable; Gong's are extended by adding elements). Whyte's own implementation notes show that written definitions per score level are what fixed rep-to-rep optimism variance. A rubric-as-markdown with per-stage "not applicable" rules (Zime's pattern) and score-level definitions, editable in git, is both more faithful to the customer's playbook and auditable.

5. Local-first and read-mostly. All the commercial products are SaaS with recording, retention and lock-in concerns (Gong export complaints, EU/CA recording reviews). A plugin that reads via HubSpot's official MCP or Agent CLI, keeps transcripts and scores on the user's machine, and proposes rather than writes CRM changes matches the Anthropic-official pattern and the RevOps audit posture in the rework piece. Zime and FitNova prove the appetite for "no data leaves your machine".

6. A price class that does not exist. Gong's median contract is $54,900/yr plus a $5-50k platform fee and a ~15-seat floor; Clari's median is $76,000 with 25-50 seat minimums; People.ai has ~25-seat minimums. The HubSpot-native options are thin: Meddicc Score ($69/team/mo, single LLM number), Ebsta ($50-70/user/mo, Salesforce-first), Sybill and Fathom (field autofill, no adoption analytics). An open plugin running at API cost (jeff266 reports ~$10-20/month for nightly scoring plus light Slack use) opens methodology measurement to the 3-30 rep HubSpot teams that Force Management and Gong do not serve.

7. Rep-first briefing and retro. Salesloft's Monday email and ooligo's Friday self-review are the only sourced, scheduled, rep-facing patterns found, and neither reports framework coverage. A daily briefing that says "on today's three calls you have no Economic Buyer identified on Acme, quote from last call: '...'" and a weekly retro that shows the rep's own MEDDPICC coverage versus last week, delivered to the rep before any manager, is unoccupied ground and addresses the surveillance objection directly.

8. HubSpot depth where the methodology tools are Salesforce-first. Momentum, Rattle, iSeeit, Force Management's Opportunity Manager and People.ai are Salesforce-only or Salesforce-centric. HubSpot's own Smart Deal Progression is suggestion-only and has no methodology scoring; its Conversation Intelligence needs Sales Hub Pro/Enterprise. Reading HubSpot calls, meetings and emails through the official MCP and scoring them locally is a gap the HubSpot marketplace currently fills with a single small app.

Open questions the plugin design should settle early (surfaced by this research):
- Which "adoption" definition is primary: evidence-scored adherence per call (hardest to game), field completion (what HubSpot dashboards already show), or share of reps above a coverage threshold (what CSO Insights measured)? Reporting all three with the same denominator avoids the vendor ambiguity in section 1.3.
- How to handle stage confounding in the adoption-to-outcome correlation. Ebsta's own teardown shows coverage rises with stage; the honest comparison is coverage *at a fixed stage* (e.g. by end of Discovery) against eventual outcome, which Ebsta 2023 reports as "71% more likely to close" when two criteria were complete by end of stage two.
- Where transcripts come from on HubSpot-only teams: HubSpot Notetaker and Conversation Intelligence require Sales Hub Pro/Enterprise; Fathom's free tier plus its HubSpot sync is the cheapest path to transcripts on a deal record, and Fathom, Sybill and People.ai now expose MCP.
- Whether to verify quotes deterministically (Stratyfix pattern) at the cost of rejecting paraphrased evidence, or to allow near-matches with a similarity threshold and flag them.
- Whether the weekly retro is rep-only by construction (ooligo's argument that manager auto-cc destroys the signal within a week) or manager-visible with rep consent.

Adjacent risks to watch: HubSpot could add MEDDPICC scoring to Smart Deal Progression at any release; Attention's gtm-superintelligence is the most capable open competitor and is vendor-funded; Backstory (People.ai) now exposes MCP and could become the data layer for a Salesforce equivalent. The defensible position is not the scoring prompt but the measurement layer (adoption over time, outcome correlation, verified evidence) and its openness.
