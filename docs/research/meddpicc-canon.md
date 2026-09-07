# MEDDPICC canon: reference for an LLM-judged, evidence-based qualification rubric

Compiled 2026-09-07. Purpose: give a transparent factual base for encoding MEDDPICC as a rubric that an LLM judge applies to sales calls, emails and CRM notes, and for measuring whether reps have actually adopted the method after training.

Source tiers used throughout (marked in brackets):
- [T1] Canonical or primary: PTC-lineage authors (Dunkel, Napoli, McMahon, Lahoutifard), MEDDICC Ltd / Andy Whyte, MEDDIC Academy, Force Management, MEDDICC.com element pages.
- [T2] Large-sample benchmark data: Ebsta x Pavilion reports (3M to 4M+ opportunities), Gong Labs, Korn Ferry / CSO Insights, peer-reviewed research.
- [T3] Practitioner and vendor guides (Closing Foundry, Backdrop, Nimitai, Prolifiq, CRO Expert, AmpUp, Hyperbound, etc.). Useful for scales and anchors; numbers are usually unaudited.
- [T4] AI-generated content farms and circular citations (pulserevops.com "2027" pages, coffee.ai benchmark tables, the "18% / 24%" claim). Quoted only to show what is circulating; not treated as evidence.

---

## 1. Canon and lineage

### 1.1 Origin at PTC

- MEDDIC was created inside Parametric Technology Corporation (PTC). MEDDICC Ltd dates it to 1996, "created by Dick Dunkel who was working under the leadership of PTC SVP John McMahon and in collaboration with teammate Jack Napoli". Dunkel and Napoli studied past and present opportunities to answer why PTC won, why it lost and why deals slipped, and found that "for every time without fail, they could attribute a deal's success or failure to six specific areas": Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion. [T1] https://meddicc.com/resources/who-created-meddic
- Jack Napoli's own account: he "witnessed the birth of MEDDIC when Dick wrote it on the white board for the first time"; "the actual biological father of MEDDIC is Dick Dunkel"; "MEDDIC/MEDDICC/MEDDPICC is John McMahon's sales brain codified; Dick Dunkel was the first to write it down". Napoli estimates ~3,000 customer-facing PTC employees learned it through company education events. He also says elements (champion vs coach, EB access, decision criteria/process, quantified pain) were taught "before the acronym MEDDIC existed". [T1] https://www.salesmeddic.com/blog/origin-of-meddic and https://thinkinsights.net/consulting/meddpicc/
- MEDDIC Academy (Darius Lahoutifard, ex-PTC Southern Europe) frames it as teamwork by "a dozen trailblazers" in the early 1990s under CEO Steve Walske, with Anne Gary, Jack Napoli and Dick Dunkel as the internal training team who formalised it as a checklist and taught a simplified version in new-hire onboarding. [T1] https://meddic.academy/definition-meddic/ and https://meddic.academy/meddic-sales-methodology-checklist/
- Business context that every school repeats: PTC grew from roughly $300M to $1B in about four years and posted 40+ consecutive quarters of growth (Whyte says 43) while "never missing a target". [T1] https://meddicc.medium.com/lessons-learned-from-implementing-meddpiccr-a-year-on-25cafef1330b ; https://www.forcemanagement.com/maximizing-meddicc-with-a-solid-sales-process-and-clear-value-message
- Design logic worth preserving in a rubric: MEDDIC was reverse-engineered from lost and slipped deals. It is "a checklist of what a winnable deal contains, built from the post-mortems of the ones that were lost", not a pitch framework. [T3] https://www.closingfoundry.com/insights/meddic-vs-meddpicc

### 1.2 Commercialisation timeline (who owns which word)

| Year | Event | Source |
|---|---|---|
| early 1990s / 1996 | MEDDIC formalised at PTC (see 1.1) | meddicc.com, meddic.academy |
| 2006 | Jack Napoli's CIS ("The Godfather of MEDDIC") starts in-person MEDDIC training; Lahoutifard's 01consulting starts MEDDIC and MEDDPICC training the same year | https://meddic.academy/definition-meddic/ |
| 2013 | Lahoutifard publishes MEDDPICC material on Slideshare and later registers the MEDDPICC® trademark (US), which he still owns | https://meddic.academy/definition-meddic/ ; https://meddpicc.net/ |
| 2017 | MEDDIC Academy launched, first online MEDDPICC courses; test-based "MEDDIC Certified" from 2018 | https://meddpicc.net/ |
| 2019 | Andy Whyte publishes "Lessons learned from implementing MEDDPICC a year on" (Poq, London): confidence scoring 1 to 10 per letter with written criteria, aligned to stage gates | https://meddicc.medium.com/lessons-learned-from-implementing-meddpiccr-a-year-on-25cafef1330b |
| 2020 | Whyte's book "MEDDICC: The ultimate guide to staying one step ahead in the complex sale" (foreword/commentary by Dunkel and Napoli; 100k+ copies claimed). Lahoutifard's "Always Be Qualifying" published around the same time ("the first book on MEDDIC, I wrote it last year", Oct 2021 interview) | https://andywhyte.com/book/ ; https://meddic.academy/everything-you-ever-wanted-to-know-about-meddic-meddpicc-and-never-dared-ask/ |
| 2021 | John McMahon, "The Qualified Sales Leader" (five-time CRO; board member at Snowflake, MongoDB): MEDDPICC as "map and GPS", six-stage process with EB meeting as go/no-go | https://www.businessfloss.com/books/the-qualified-sales-leader |
| 20+ years | Force Management (co-founded by John Kaplan, ex-PTC SVP International Sales Ops) sells MEDDICC / MEDDPICC training paired with Command of the Message | https://www.forcemanagement.com/b2b-sales-consulting-john-kaplan ; https://www.forcemanagement.com/offerings/meddicc |

Trademark note: "MEDDPICC®" is a registered mark of Darius Lahoutifard / MEDDIC Academy; "MEDDICC™" is used by Andy Whyte's MEDDICC Ltd (UK). Both camps publish near-identical letter definitions but differ on the I (see 1.5) and on Metrics sub-structure.

### 1.3 The variants

| Variant | Letters | Who uses / notes |
|---|---|---|
| MEDDIC | Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion | Original PTC six. Still the base at PTC-alumni shops. |
| MEDDICC | MEDDIC + Competition (second C) | Force Management's default acronym; Andy Whyte's book title; Gong says "at Gong, we use MEDDICC" while listing eight elements including paper process. Caution: "a few teams use the second C for Closing or Compelling Event instead, so when someone says MEDDICC, it is worth checking which C they mean" (Closing Foundry). |
| MEDDPIC | MEDDIC + Paper Process (no Competition) | Force Management describes it: "In many MEDDIC frameworks used by B2B companies, the paper process is implied within the D for decision process" and MEDDPIC pulls it out. |
| MEDDPICC | MEDDIC + Paper Process + Competition (eight) | MEDDICC Ltd's "preferred variation"; MEDDIC Academy's trademarked course; McMahon's book; Ebsta reports it as the most popular methodology. |
| MEDDDPICC | adds a third D for "Documents" (ooligo) | Fringe. |
| MEDDPICC + "Pivotal events / Implications of inaction" (10 fields) | [T4] pulserevops only | Not canon. |

Sources: https://www.closingfoundry.com/insights/meddic-vs-meddpicc ; https://www.forcemanagement.com/blog/meddic-vs.-meddpic-the-meaning-difference-and-benefits-of-each-for-sales-qualification-force-management ; https://meddicc.com/meddpicc-sales-methodology-and-process ; https://www.gong.io/blog/gong-on-gong-strategic-enablement-initiatives ; https://ooligo.com/en/learn/medddpicc/

Whyte's argument for the longer variants: "when the MEDDIC creator, Dick Dunkel himself uses alternative variants as do MEDDIC all-time greats like John McMahon, Jack Napoli, and John Kaplan there must be something in the more detailed variants". https://meddicc.buzzsprout.com/1423969/episodes/7722925-masters-of-meddicc-what-is-the-correct-acronym-for-meddic-is-it-meddic-meddicc-meddpicc-bonus-episode

### 1.4 Letter definitions by school (verbatim where possible)

| Letter | MEDDICC Ltd (Whyte) | Force Management | MEDDIC Academy (Lahoutifard) | McMahon (TQSL) |
|---|---|---|---|---|
| M Metrics | "quantifiable measures of value that your solution provides. They typically fall into three categories: Economic, Efficiency, Risk." Split into M1 (outcomes delivered for existing customers), M2 (personalised to this customer), M3 (validated M2 after go-live). | "Quantifiable measurements of the business benefits of the solution" | "Quantification of the potential gain and, ultimately, the economic benefit" | "quantifiable economic benefit... prove exactly how much money you will save or make the customer" |
| E Economic Buyer | "the person with the overall authority in the buying decision. They have the power to say yes when others say no, and say no when others say yes." Has veto, P&L responsibility, access to discretionary unbudgeted funds. | "Individual within the organization who has the final yes"; "the decision-maker with the ability to move and alter spend to create budget", not merely someone with budget | "Interaction with the person who has decision control on the funds for the PO" | "the individual with discretionary budget authority"; EB meeting is the go/no-go stage |
| D Decision Criteria | "the various criteria by which a decision to purchase your solution will be judged". Three kinds: Technical, Economic, Relationship ("3D decision criteria"). | "Formal solution requirements in which each decision maker will evaluate the solution" | "Criteria used by the company to make the purchase decision and choose among options" (plus their "Value Triangle") | capabilities and requirements "developed during Discovery and finalized in Scoping"; rep gains control by helping the Champion write them |
| D Decision Process | "the series of steps that the buyer will follow to make a decision", two parts: technical validation and business approval. "Engagement is not progress." | "How the customer will evaluate, select, and purchase a solution" | "Process defined by the company to reach the purchase decision" | "specific events, stakeholders, and timeframes" |
| P Paper Process | "the series of steps that follow the Decision Process, detailing how you will go from decision to signature" (legal review, security sign-offs, vendor questionnaires, MSA). "You cannot accurately forecast without fully understanding the Paper Process." | "legal, procurement, and administrative steps required to finalize a deal" | "Formal procurement process that the customer has defined internally for all suppliers, including security review, legal, purchasing" | "legal, security, and procurement workflow required to get the actual contract signed" |
| I Pain | "Implicate the Pain": Identify, Indicate, Implicate. "If your customer doesn't truly understand the consequences of the pain, if they aren't implicated in it, there will be no urgency." | "Identify Pain: Pain is the catalyst for the buyer solving the problem within a set timeframe" | "Identify Pain: Actual pains at the company that would require your product/service to be relieved" | "severe business problem driving the urgency to buy right now. If there is no urgent pain, there is no sale." |
| C Champion | "a person who has power, influence, and, subsequently, credibility within the customer's organization and who is willing and able to assist you". "No Champion, No Deal." Contact vs Coach vs Champion. | "A person with influence in the buying organization. They have an investment in your solution being selected." Three criteria: influence, actively sells on your behalf, vested interest. | "Powerful and influential persons at the company who are favorable to your solution" | influence + access to the EB + personal win; "If your contact cannot or will not secure a meeting with the Economic Buyer on your behalf, they are not a Champion." |
| C Competition | "any person, vendor, or initiative competing for the same funds or resources you are" (rivals, self-build, do nothing). "Rule one of sales is Do Not Knock Your Competition." | "Any alternatives to purchasing your solutions including Do nothing and Do it internally" | "alternatives... including another supplier, internal developments, or simply status quo (i.e., no decision)" | "direct competitors, internal workarounds, and the status quo" |

Sources: https://meddicc.com/what-is-meddpicc/metrics ; /economic-buyer ; /decision-criteria ; /decision-process ; /paper-process ; /implicate-the-pain ; /champion ; /competition ; https://www.forcemanagement.com/blog/make-meddicc-work-for-your-sales-organization ; https://www.forcemanagement.com/blog/how-meddicc-helps-win-with-decision-makers ; https://meddic.academy/meddic-sales-methodology-checklist/ ; https://www.bookey.app/book/the-qualified-sales-leader

### 1.5 The "Identify" vs "Implicate" split

- Original PTC wording is Identify Pain. Force Management, MEDDIC Academy, McMahon and most CRM templates keep "Identify".
- MEDDICC Ltd relabels the I as "Implicate the Pain" with a three-step ladder: Identify (a problem exists), Indicate (broader impacts), Implicate (the customer feels the consequences of inaction). Practitioners summarise it as: average sellers identify ("our reporting is slow"), good sellers indicate ("costs ~40 hours/month"), elite sellers implicate ("you miss board deadlines, your CFO loses confidence"). https://meddicc.com/what-is-meddpicc/implicate-the-pain ; https://prospeo.io/s/implicate-the-pain ; https://www.exec.com/learn/meddpicc-the-complete-guide
- For a rubric this matters: "Identify" is satisfied by a named problem; "Implicate" requires a buyer-stated consequence and cost of inaction. The rubric below scores the ladder, so both schools can read it.

### 1.6 Which variant dominates in UK/EU SaaS enablement

- The two most visible commercial MEDDIC houses in Europe teach the eight-letter form: MEDDICC Ltd (London; Whyte was EMEA lead at Branch and implemented MEDDPICC at Poq, London) and MEDDICC.se (Sweden, HubSpot-centred implementations). https://meddicc.medium.com/lessons-learned-from-implementing-meddpiccr-a-year-on-25cafef1330b ; https://www.meddicc.se/en/post/quick-channel-meddpicc-success
- Ebsta (London) x Pavilion 2023 benchmark (3.2M opportunities, 364 companies, $37B pipeline, 2022 data): adoption of a sales methodology doubled from 11% to 21% in 2022; "MEDDPICC, or a variation of, was the most popular at 61%"; "43% of high performers had a structured sales methodology". [T2] https://www.ebsta.com/wp-content/uploads/2023/02/2023-B2B-Sales-Benchmark-Report.pdf (p.6, p.11)
- Ebsta's 2024 report benchmarks only two methodologies by name, SPICED and MEDDPICC, and its 2025 report is framed entirely around MEDDPICC-style qualification. [T2] https://www.ebsta.com/wp-content/uploads/2024/02/B2B-Sales-Benchmarks-2024_.pdf
- UK-specific practitioner claim: MEDDICC "is especially popular among London's Series B-D SaaS companies"; suggested threshold "if your average deal value is above £15k, MEDDICC should probably be your default framework" (unaudited). [T3] https://www.gotiller.com/blog/meddicc-framework-complete-guide-for-uk-sales-teams-2025
- Closing Foundry (UK) frames the choice in sterling: sub-£100k, sub-90-day cycles use MEDDIC; complex enterprise use MEDDPICC; "MEDDPICC, popularised through Andy Whyte's work and book, is the version most enterprise SaaS teams now use". [T3] https://www.closingfoundry.com/insights/meddic-vs-meddpicc
- US hiring data for contrast: The CRO Report found MEDDIC/MEDDPICC in 117 of 1,298 executive sales postings (9.0%), second only to "consultative selling" (13.2%); "most postings use the terms interchangeably... the trend is toward MEDDPICC". [T3] https://thecroreport.com/blog/sales-methodology-adoption-rates/
- Working conclusion: in UK/EU SaaS enablement the eight-letter MEDDPICC (with Competition and Paper Process) is the modal form; "MEDDICC" is used loosely as a brand for the whole family. A rubric should score all eight and let a team switch off P or the second C for lighter motions.

---

## 2. The eight elements: definition, questions, evidence, failure modes, scoring

Format per element: canonical definition and sub-structure; rep questions (from Gong, MEDDICC.com, McMahon, Nimitai, Prospeo, Qwilr, Terasu); strong vs weak evidence; failure modes; published scoring anchors.

### 2.1 Metrics

Definition. Quantified value the buyer expects, in the buyer's own KPIs and time horizon; MEDDICC Ltd's M1/M2/M3 ladder (proof points from other customers, metrics personalised to this customer, validated post-go-live). Force Management: connect metrics to each decision-maker's priorities ("Efficiency savings of 25% may be important to an operational manager, but not as motivating to a CRO who is zeroed in on doubling ARR"). https://meddicc.com/what-is-meddpicc/metrics ; https://www.forcemanagement.com/blog/how-meddicc-helps-win-with-decision-makers

Rep questions.
- "What do you want to achieve? How will you measure success?" (Gong) https://www.gong.io/blog/meddic-sales-process
- "Which number, when it moves, tells you this succeeded?" "What is this problem costing you monthly today?" "Do you have an internal payback-period threshold?" (Terasu) https://terasu.koromo.io/en/blog/meddpicc-sales-framework
- "How do you define and report on success?" (Qwilr) https://qwilr.com/blog/25-meddpicc-questions/
- "If this project succeeds, what does that mean for you personally?" (Prospeo) https://prospeo.io/s/meddpicc-questions
- Whyte's Three Whys as a test: Why anything? Why you? Why now? Metrics are "essential to answering these questions". https://meddicc.com/what-is-meddpicc/metrics

Strong vs weak evidence.
- Strong: a number the buyer said out loud, with current value and target ("reduce DSO from 52 to 38 days, freeing $4.2M"), a time horizon, and ideally the EB's agreement that it is the KPI for the project. "The customer openly uses our Metrics, or equivalent ones, as the KPIs that will define the success of the project" is Whyte's 9-10 anchor. https://meddicc.com/resources/lessons-ive-learnt-since-implementing-meddic
- Weak: rep's ROI model with no buyer number; generic industry stat; "improve productivity"; "faster cash collection". Backdrop's rule: "A number the buyer said out loud, with the current value and the target. Not your ROI model." https://www.getbackdrop.ai/tools/meddpicc-template
- MEDDIC Academy's caution: knowing the pain costs $1M every six months is "half of the metrics. You know why they should look into something, but you don't know why they should buy your product." https://meddic.academy/everything-you-ever-wanted-to-know-about-meddic-meddpicc-and-never-dared-ask/

Failure modes. Vanity or efficiency metrics that the EB does not care about; rep-projected numbers logged as buyer numbers; metrics never revalidated post-sale (M3) so renewals start from scratch; confusing quantified pain with the value of your solution.

Data. Ebsta 2023: Metrics was the least-used element for mid and low performers (54% / 21% / 9% usage top/mid/low) and, with Decision Criteria and Paper Process, "least populated but had the biggest impact" (+206% win rate when all three completed). Ebsta 2023 INBOUND deck: "Qualifying Metrics and Decision Criteria improves win rate by 37%". https://www.ebsta.com/wp-content/uploads/2023/02/2023-B2B-Sales-Benchmark-Report.pdf ; https://www.ebsta.com/wp-content/uploads/2023/10/Ebsta-x-Sprocketeer-B2B-Sales-Benchmarks-INBOUND.pdf

Published anchors. Nimitai 0-3: 0 no number; 1 generic industry metric mentioned by rep; 2 specific metric stated by buyer, no EB validation; 3 specific, time-bound, validated by the EB. CRO Expert 0-2: pain not quantified / rough estimate given by prospect / specific dollar or KPI impact confirmed with evidence. Whyte 1-10: 1-3 "assumption of the Metrics based on outside information or initial conversations"; 9-10 customer uses our metrics as project KPIs. https://nimitai.com/blog/meddpicc-template ; https://cro.expert/blog/meddpicc-sales-qualification-guide ; https://meddicc.com/resources/lessons-ive-learnt-since-implementing-meddic

### 2.2 Economic Buyer

Definition. The one person with overall authority: veto power, P&L responsibility, discretionary funds, "can say yes when others say no, and no when others say yes". Whyte warns against applying veto literally ("all roads lead to the CEO"), against assuming the EB is static across deals, and against assuming the EB "only cares about price" (a sign the rep is too low on the value pyramid). https://meddicc.com/what-is-meddpicc/economic-buyer ; https://meddicc.com/meddicc-media/medmen-s1-ep6-economic-buyer ; McMahon: technical buyers "love the features"; EBs "only care about the financial return"; the EB meeting confirms pain priority, funds and timing and is the go/no-go stage. https://www.businessfloss.com/books/the-qualified-sales-leader ; https://sobrief.com/books/the-qualified-sales-leader

Rep questions.
- "Who is involved in the final purchasing decision?" "What would success look like for you?" (Gong)
- "Walk me through how a decision of this size gets made here, who signs the actual contract, and who else needs to be comfortable before they sign?" (Nimitai, avoids "are you the decision maker?") https://nimitai.com/blog/meddpicc-discovery-questions
- "Whose budget does this come from, and what is that person's discretionary signing limit?" "Will I be able to meet with them as part of this process?" (Qwilr)
- To the EB (McMahon): how does this rank against other priorities; is budget available or reallocatable; what remains in the decision process.

Strong vs weak evidence.
- Strong: EB named by name and role by the buyer, not inferred from the org chart; rep has met the EB (or has a dated, champion-arranged meeting); EB has confirmed priority, funds and timeline; EB agrees with the Metrics. Anchors: "Met directly, sponsorship confirmed" (Terasu 2/2); "Direct relationship established; attended at least one meeting" (CRO Expert 2/2); "EB actively engaged and supportive" (rework 3/3).
- Weak: "CFO signs anything over $50k, we have not met him" (Backdrop example scored 1); a senior title picked by the AI or rep; "we'll find them later".

Failure modes. EB-by-title; treating the VP who took the first call as EB; single EB assumption across product lines; late EB discovery (Ebsta 2024: "if the economic buyer raises ROI after solution presented, the likelihood of closing drops by 79%"). https://www.ebsta.com/wp-content/uploads/2024/02/B2B-Sales-Benchmarks-2024_.pdf

Data. Gong (9,056 opportunities, 2020): deals without a decision-maker (VP, CXO, MD) on web meetings are "80% less likely to close"; enterprise deals (>90 days, $100k+) "233% less likely"; win rates highest when the DM is an approver rather than an over-involved evaluator. https://www.gong.io/blog/heres-how-selling-to-decision-makers-affects-your-win-rates-ignore-at-your-own-risk . Gong 2026: win rates drop ~6% when an evaluation starts with an executive but rise ~5% when executives join around the third touchpoint. https://www.gong.io/blog/when-and-how-to-multi-thread-when-selling-to-executives . Ebsta 2025 (655k opps / $48B): "When decision makers are actively involved in the first 2 stages of the sales process, win rates rose by 55%, and if the engagement score with the decision maker remains above 40 throughout the sales cycle, the win rate quadruples". Ebsta 2024: top performers "241% more likely to have the economic buyer engaged before the solution presented stage". Ebsta 2023: EB usage 85% top / 29% mid / 8% low performers. https://benchmarks.ebsta.com/hubfs/V3%202025%20Benchmark%20Report/gtm_benchmarks_digital_report.pdf

Published anchors. CRM picklist ladders: "Not identified / Identified / Meeting scheduled / Active relationship" (CRO Expert); "Met / Identified / Not identified" (Coffee); "Identified / Met / Engaged / No Access" (CRO Report). Nimitai: "EB scoring caps at 1 until you have actually met them on a call".

### 2.3 Decision Criteria

Definition. The principles, guidelines and requirements the organisation will judge the purchase against. MEDDICC Ltd's three dimensions: Technical, Economic (CapEx/OpEx, contract structure, ROI, wider business case), Relationship (trust, references, partner ecosystem). Sellers are expected to uncover and shape criteria ("set traps for your competitors"). McMahon: criteria "developed during Discovery and finalized in Scoping"; changes to criteria signal shifts in deal control. https://meddicc.com/what-is-meddpicc/decision-criteria ; https://meddicc.com/meddicc-media/medmen-3d-decision-criteria ; https://www.appdirect.com/blog/decoding-meddicc-andy-whyte-breaks-down-the-3-key-parts-to-selling

Rep questions.
- "What are the top three criteria you'd like to see in a product? How do you plan to justify this purchase to others involved?" (Gong)
- "Are the decision criteria weighted, and can you share which are most important?" "Are there additional intangible factors?" (Qwilr)
- "If you were writing the evaluation scorecard today, what are the five rows and how are they weighted?" "What disqualifies a vendor in the first fifteen minutes of a demo?"
- McMahon's inspection questions: "Did you assist your Champion in writing the criteria? Which of our differentiators are included in the final criteria? Have any competitors influenced changes in the criteria?"

Strong vs weak evidence.
- Strong: criteria in the buyer's words, ideally a document or scorecard; weighted; covers technical, economic and relationship; includes your differentiators (evidence of shaping); validated with more than one stakeholder ("Criteria validated with multiple stakeholders, mapped to our solution", rework 3/3).
- Weak: "integrations, price, support" (generic, Nimitai score 1); criteria inherited from another vendor's RFP (Nimitai 2); criteria known from one stakeholder only.

Failure modes. Working only technical criteria; taking "they like us" as criteria; not noticing criteria changing late (competitor influence); evaluating against your own feature list.

Data. Ebsta 2023 usage 76% / 24% / 12.5% by performer tier; one of three "least populated, biggest impact" elements. Ebsta 2023 INBOUND deck: MEDDPICC without Metrics, EB and Decision Criteria at stage 2 "resulted in a 31% drop in win rates".

Published anchors. Nimitai 0-3: none / generic / specific but inherited / specific, shaped by you, aligned with differentiation. Terasu 0-2: unknown / main criteria known / weighting agreed. CRO Expert 0-2: unknown or assumed / partial list shared verbally / full written criteria documented from the prospect.

### 2.4 Decision Process

Definition. The ordered steps, people and dates from today to a decision; two parts (technical validation, business approval). "Engagement is not progress"; "the Decision Process is the number one thing that dictates your time to close"; "60% of deals are lost to inertia" (MEDDICC Ltd, unsourced). Force Management: buyers often do not know or will not share it, so "triangulate the truth" rather than take the first answer at face value. https://meddicc.com/what-is-meddpicc/decision-process ; https://www.forcemanagement.com/blog/how-meddicc-helps-win-with-decision-makers

Rep questions.
- "Walk me from today to the day we'd sign: what are the steps, who has to approve, and roughly when?" (Nimitai, Prospeo)
- "Has a deal like this ever stalled internally? What caused it?" "Who has veto power that we haven't talked to yet?" (Prospeo)
- "When is the next steering or budget meeting, and what must be decided there?" (Terasu)
- McMahon: "What events will be utilized to evaluate solutions? Who are the stakeholders? Has the decision process changed since it was developed, and who influenced those changes?"

Strong vs weak evidence.
- Strong: named stages with owners and dates, confirmed by the buyer, tested for accuracy at each stage; a mutual action plan or close plan the buyer has agreed; Whyte's 7-8 anchor: "We strongly understand the Decision Process, have validated it with our Champion, and have tested its accuracy at each stage." https://meddicc.com/resources/lessons-ive-learnt-since-implementing-meddic
- Weak: "this quarter"; "security review then procurement" inferred from how they bought last time (Backdrop example scored 1: "the last purchase's process, assumed to repeat"); a process with steps but no owners.

Failure modes. Mistaking activity (demos, reference calls) for progress; missing a committee or board cycle; no critical event (SPICED critics: "A rep can document a complete decision process for a deal with no reason to happen this quarter", https://orm-tech.com/blog/spiced-vs-meddic/ ); Ebsta 2025: "76% of B-player deals lack critical events".

Data. Ebsta 2023 usage 56% / 31% / 22%. Ebsta 2024: if the Qualification stage runs 50% longer than average the deal is 120% more likely to slip; win rates fall 34% when a close date slips 1-4 weeks and a further 67% beyond a month. Ebsta 2025 Qualification Report: "Economic Buyer, Decision Process and Paper Process are often left incomplete". https://www.sendtrumpet.com/driving-profitable-growth-through-smarter-qualification-ebsta-x-trumpet-report-2025

Published anchors. Nimitai 0-3: "this quarter" only / named stakeholders, no dates / milestones + owners + approximate dates / mutual action plan with CFO calendar slot booked. rework 0-3: no understanding / high-level from one person / detailed with stages and timelines / validated, stakeholders identified, milestones scheduled.

### 2.5 Paper Process

Definition. Everything between "yes" and signature: legal review, security questionnaires, DPA, MSA redlines, procurement intake, vendor onboarding, PO issuance, signature routing. Separated from Decision Process "to keep the deal moving"; "You cannot accurately forecast without fully understanding the Paper Process." MEDDIC Academy: understand it early "before they can place an order or sign a contract... quite early in the sales process". https://meddicc.com/what-is-meddpicc/paper-process ; https://meddic.academy/everything-you-ever-wanted-to-know-about-meddic-meddpicc-and-never-dared-ask/

Rep questions.
- "What paperwork do you ask vendors to provide before a purchase is complete?" (Gong)
- "Who runs your security review here, and how long does it typically take for a SaaS vendor of our size?" "Do you have a preferred MSA template, or do vendors start from theirs, and who in legal owns the redlines?" "Walk me through the last vendor you onboarded." (Nimitai)
- "Can we start the security questionnaire in parallel with the evaluation?" "Has a deal ever been killed in legal review?" (Prospeo)
- "What's the longest and shortest this has taken you before?" (Terasu)

Strong vs weak evidence.
- Strong: named owners for legal, security, procurement and finance; durations from the buyer's own precedent; questionnaire received/answered; MSA path agreed; vendor code assigned; steps already in motion.
- Weak: "not discussed"; "procurement acknowledged, process unknown"; timelines assumed from a prior purchase.

Failure modes. Asking too late ("skipped 71% of the time" in Nimitai's 350-call sample; "the most-skipped dimension"); treating verbal yes as closed; Q4 verbal commits signing in Q1. Timing caution from Prospeo: raising paper process in first discovery "signals that you're more focused on closing than on solving the buyer's problem", so a per-interaction judge should not penalise its absence in early-stage calls.

Data. Ebsta 2023: Paper Process was one of the three least-populated, highest-impact elements (+206% with Metrics and DC); usage 57% / 22% / 36%. Gong's enablement lead on their initiative board: "the team is almost always nailing discovery questions, but there's a lack of adoption and, potentially, understanding of the paper process". https://www.gong.io/blog/gong-on-gong-strategic-enablement-initiatives . The widely repeated "deals without a confirmed paper process slip 38% of the time in the final 30 days (Ebsta/Pavilion 2025)" [T4] does not appear in the 2025 report text; treat as unverified.

Published anchors. Nimitai 0-3: not discussed / acknowledged, no detail / security questionnaire received and answered, MSA template identified / legal review scheduled, security cleared, vendor code assigned. CRO Expert 0-2: not discussed / procurement acknowledged, process unknown / full legal-procurement timeline confirmed with named owner.

### 2.6 Pain (Identify / Indicate / Implicate)

Definition. The business problem serious and urgent enough to fund change, owned by the EB or their reports, with a cost of inaction. Force Management: "we get delegated to who we sound like"; if the pain is not big enough, sellers cannot reach power. Their Command of the Message discovery method: "you can't tell anybody they have a problem... the more you ask great two-sided discovery questions... the more that person will convince themselves"; TED prompts ("Tell me about", "Explain for me", "Describe for me"). https://www.forcemanagement.com/blog/stand-in-the-moment-of-pain

Rep questions.
- "How does [problem] affect your business, financially and otherwise? What would happen if everything stayed the same?" (Gong)
- "What happens if you don't solve this by [timeframe]?" "How are you measured in your role?" "Who else is affected by this, and how?" "What's the second-order effect you're most worried about?" (Prospeo implicate ladder)
- "What have you already tried, and why didn't it stick?" (Terasu)
- McMahon: articulate pain level, ownership and urgency, tied to a solution.

Strong vs weak evidence.
- Strong: buyer-stated, quantified, dated, with a named consequence and an owner (Backdrop example scored 3: "Stale number in a board dashboard, in front of the CFO. Two analyst days per incident, roughly two incidents a month. Board pack goes out on the 5th."); the buyer articulates cost of inaction unprompted or in their own words after silence.
- Weak: rep-stated pain that the buyer merely acknowledges ("yeah, that's annoying" extracted as high pain); "they would like to improve X"; latent pain not yet active.

Failure modes. Feature-mapping instead of implicating; rushing from identify to demo; projecting pain from rep's own framing; no personal stake surfaced.

Data. Ebsta 2023: Identify Pain is the most-used element at every tier (78% / 64% / 66%), so on its own it discriminates least between performers. Winning by Design (vendor training data): reps who uncover Impact "sell 53% more against the same opportunity volume" than reps who stop at Pain. https://www.supered.io/blog/spiced-sales-methodology/

Published anchors. Nimitai 0-3: pain unnamed / rep-stated, buyer acknowledged / buyer-stated qualitatively / buyer-quantified with a specific business cost. CRO Expert 0-2: vague / described not quantified / quantified, linked to a business case, confirmed by EB.

### 2.7 Champion

Definition. Three traits that must all be present (Whyte, Force Management, McMahon, AmpUp): (1) power and influence inside the account, (2) actively sells for you when you are not in the room, (3) a vested personal interest in your success. Missing any one makes the person a Coach (gives information and introductions but cannot move the deal) or a Contact. "No Champion, No Deal." Champions must be built, prepared for pushback (Three Whys), and "continually tested". McMahon's power matrix: influence x authority; those with influence and authority are business Champions, influence without authority can be technical Champions, no influence means coach at best. https://meddicc.com/what-is-meddpicc/champion ; https://www.forcemanagement.com/blog/how-meddicc-helps-win-with-decision-makers ; https://www.befreed.ai/book/the-qualified-sales-leader-by-john-mcmahon

Champion tests (what the judge should look for as demonstrated action).
- Access test: can they get you a meeting with the EB? McMahon: "If they refuse or cannot make it happen, they do not have the power of a true Champion."
- Risk test: have they put their reputation on the line, presented your case in a meeting you were not in? (CRO Report)
- Personal-win test: can the rep say what this individual gains? (CRO Report, MEDDIC Academy: "What is their personal win in this context?")
- Articulation test: can they explain why change, why now, why you, in their organisation's language, without your slides? (AmpUp)
- Proactive-intel test: do they volunteer internal information before being asked? ("Tuesday. She texted me that procurement wants to consolidate vendors this quarter" vs "he answers when I reach out")
- Prospeo's three-step false-champion sequence: ask for the EB intro; ask them to present your business case internally; ask what happens if the project is not funded. "A false champion stalls at step one."
- Precedent test: "What happened the last time you bought something like this?"
Sources: https://www.ampup.ai/resources/sales-champion-qualification-framework ; https://thecroreport.com/blog/meddpicc-champion/ ; https://revcentricpartners.com/blog/meddic-champion-criteria-identify-test-develop ; https://www.accountmap.ai/blog/identify-sales-champions ; https://prospeo.io/s/meddpicc-questions ; https://www.meddicmondays.com/post/think-you-have-a-champion-prove-it

Strong vs weak evidence.
- Strong: observable actions taken without the rep present: introduced new stakeholders unasked, forwarded materials and reported reactions, booked the EB meeting, presented internally, defended the deal against a competitor or finance pushback, shared internal documents, co-authored the business case. Anchor: "delivering meetings, sharing internal documents, defending you in deal reviews" (Nimitai 3).
- Weak: "VP of Engineering, strong relationship"; friendly, responsive, "likes us"; "let me take it to my team" followed by silence ("the leading cause of late-stage deal slippage", AmpUp); "has not yet spent any internal capital on us" (Backdrop example scored 1).

Failure modes. Coach mislabelled as champion ("roughly half the people labeled as champions in any given pipeline are actually coaches or friendly contacts", CRO Report); champion without EB access; champion leaves (Weflow: "the CRM says the deal has a champion and the champion left two months ago"); single-threading; AI extraction over-claiming ("The agent identifies a coach... as a champion. AE must override.").

Data. Ebsta 2023 usage 56% / 30% / 15% by tier. Gong (1.8M opportunities, 2025): 77% of deals multi-threaded but "the ones that close successfully have twice as many buyer contacts as those that don't"; closed-won deals have 67% more contacts than closed-lost; multi-threading "boosts win rates by an average of 130% in deals over $50K". https://www.gong.io/blog/data-shows-top-reps-dont-just-sell-they-orchestrate-with-ai ; https://www.gong.io/resources/guides/the-data-backed-guide-to-multi-threading-and-team-selling . Practitioner consensus (AmpUp, Salesmotion, skipcall) calls Champion "the most predictive element" and "hardest to coach"; no public dataset isolates it.

Published anchors. Nimitai 0-3: no advocate / friendly contact, untested / one small ask delivered / delivering meetings, sharing internal documents, defending you in deal reviews. CRO Expert 0-2: friendly contact who returns calls / internal advocate, will speak up in meetings / proven champion with EB access who actively sells internally. CRM picklists: "Contact / Internal advocate / Proven champion" (CRO Expert), "Champion strength" dropdown (CRO Report). pulserevops [T4] rule quoted for illustration: "If any one [of power, influence, vested interest] is missing, the maximum score is 1."

### 2.8 Competition

Definition. Any person, vendor or initiative competing for the same funds or resources: named rivals, self-build/internal IT, other internal budget priorities, and doing nothing. Force Management: "most likely, your biggest competition when it comes to deal decision-makers is the other internal budget priorities leading to a do-nothing or do-it-internally decision". Whyte: do not knock the competition; be proactive by shaping decision criteria; "your competitors will have Champions too, and the only way you will beat them is if your Champion is stronger". https://meddicc.com/what-is-meddpicc/competition ; https://www.forcemanagement.com/blog/how-meddicc-helps-win-with-decision-makers

Rep questions.
- "What draws you to this specific product or solution?" (Gong)
- "Who else are you evaluating? Is do nothing a realistic option? Are there internal projects that could solve part of this?" (Prospeo)
- "If your platform team offered to build this in ninety days, would that win?"
- "What do you like and worry about with each?" (Terasu)
- McMahon: monitor changes to decision criteria and process as signals of competitor influence; equip the Champion against competitive traps.

Strong vs weak evidence.
- Strong: buyer names alternatives including status quo and build; buyer states where each is stronger; the rep has a differentiated plan; do-nothing has been eliminated with a quantified urgency case (Nimitai 3).
- Weak: "no competition" ("You're the only one we're talking to" is "almost always a lie, or it means they're not serious", Prospeo); competitors known by name only; do-nothing untested.

Failure modes. Ignoring status quo; late competitive surprise; knocking competitors; AI extraction missing status quo because no vendor name was spoken.

Data. Gong Labs (2016): early competitor mentions raise win odds 49%; mentions mid-to-late cycle slightly reduce them, so "you have to preemptively win the competitive battle early". https://www.gong.io/blog/competitor-mentions-science-uncovers-how-they-influence-b2b-sales . Ebsta INBOUND deck example: "Win rates drop by 36% when Competitor A is mentioned" (one customer's data). Gong ships win/loss analytics by competitor tracker. https://help.gong.io/docs/understanding-your-competitive-landscape

Published anchors. Nimitai 0-3: unknown / named alternatives known, do-nothing live / alternatives differentiated, do-nothing addressed but not closed / do-nothing eliminated with quantified urgency case. CRO Expert 0-2: none known / named but not assessed / assessed with clear differentiation documented.

---

## 3. Published scoring scales (collected)

| # | Publisher | Scale | Anchors | Total / bands |
|---|---|---|---|---|
| 1 | Andy Whyte at Poq (2019), MEDDICC Ltd guidance | 1-10 confidence per letter with written criteria | e.g. Metrics 1-3 "assumption based on outside information"; 9-10 "customer openly uses our Metrics as the KPIs"; Decision Process 7-8 "validated with our Champion, tested its accuracy at each stage" | Gate by stage: Decision Process >= 8/10 (or >= 7) to enter Negotiation. Introduced because "confidence levels would vary across salespeople based on how optimistic or pessimistic their personalities were" (Happy Ears vs Pessimists). https://meddicc.com/resources/lessons-ive-learnt-since-implementing-meddic |
| 2 | MEDDIC Academy Score Calculator / App | ~100 yes/no questions per deal, rolled to a percentage and radar chart | "flip the no's to yes"; "the lines with a NO are your to-do list" | No minimum score ("some people are tough with answers, some are soft"); red flags such as Pain under ~75 late in cycle, or Champion under 80 when 30% into the cycle; near 100% expected at close; "think twice before adding the deal to your committed forecast" at 60% three weeks from quarter end. https://meddic.academy/meddic-score-calculator-by-meddic-academy/ ; https://www.linkedin.com/posts/meddic_meddic-meddpicc-scorecard-activity-7095457275787563009-vX9G |
| 3 | Backdrop | 0-3 evidence ladder | 0 Unknown; 1 Assumed (rep inference); 2 Confirmed (buyer said it on a call, written verbatim, one source); 3 Evidenced (second person in the account or customer-produced document) | /24: 0-9 "a conversation, not a deal"; 10-15 "real, unproven"; 16-20 "forecastable with named risk"; 21-24 commit. "The line between a 1 and a 2 is the whole value of the exercise." https://www.getbackdrop.ai/tools/meddpicc-template |
| 4 | Prolifiq | 0-3 | 0 unknown; 1 assumed; 2 confirmed by one source; 3 validated by the buyer in writing or documented conversation | /24; ">= 20 with no element below 2 is genuinely qualified"; require evidence for any 2 or 3. https://www.prolifiq.com/post/meddpicc-template |
| 5 | Nimitai | 0-3 per element with element-specific anchors (listed in section 2) | evidence column mandatory: "No quote = score of 0" | /24: 0-8 poor; 9-15 developing; 16-20 strong (upside); 21-24 committed. CRM gates: no Proposal stage unless all 8 scored; no Negotiation unless >= 12; no Commit unless >= 18. "A deal at 18/24 with Paper Process at 0 is far more at risk than a deal at 15/24 with every dimension at 1-3." https://nimitai.com/blog/meddpicc-template ; https://nimitai.com/blog/what-is-meddpicc |
| 6 | Closing Foundry Deal Health Scorecard | 0-3 on buyer evidence | RAG bands | /24: 0-8 red (disqualify or restart discovery); 9-16 amber; 17-24 green. https://www.closingfoundry.com/operator-tools/meddpicc-deal-health-scorecard |
| 7 | Tech Sales Playbook | 0-3 | 0 unknown; 1 seller hypothesis or indirect signal; 2 buyer-confirmed with identified gap; 3 buyer-confirmed, specific, connected to the decision process | records source, date, confidence, gap, next action, owner per score. https://www.techsalesplaybook.com/blog/meddpicc-scorecard |
| 8 | rework.com | 0-3 | 0 Not identified; 1 Identified but not validated; 2 Validated (confirmed with prospect); 3 Documented and aligned | stage goals: early 1-2 on all; mid 2-3; late 3 on all; cannot enter Negotiation without 3 on Metrics, EB, Champion. https://resources.rework.com/libraries/pipeline-management/meddic-framework |
| 9 | "meddic-scorecard" skill (Claude skills hub) | 0-3 | 0 Unknown; 1 Identified; 2 Validated; 3 Leveraged ("actively using in deal strategy") | weighted (M, E, I, C 15%; others 10%); stage minimums 8/12/16/18/21/22 of 24 with required 3s (Pain by Qualification; + Champion; + Criteria; + EB; + Paper Process). https://claudeskills.info/skills/guia-matthieu/clawfu-skills/meddic-scorecard/ |
| 10 | CRO Expert | 0-2 | element-specific (section 2) | /16: 14-16 commit; 10-13 upside; 6-9 pipeline; <6 not qualified. Reps fill before review, not during. https://cro.expert/blog/meddpicc-sales-qualification-guide |
| 11 | Terasu | 0-2 | Unknown / Partial / Validated | /16: S 14-16; A 12-13; B 8-11; C 4-7; D 0-3 disqualify. https://terasu.koromo.io/en/blog/meddpicc-sales-framework |
| 12 | Knowlee | 0-5 weighted | 0 unknown; 3 established but incomplete; 5 fully confirmed and documented; M and E 20% each | 0-100: Strong >= 75; Workable >= 50; At-Risk >= 30; Walk Away < 30; "deal-stopper" = score 0-1 on a dimension weighted >= 15% (most common: EB access and confirmed champion). https://www.knowlee.ai/tools/meddic-qualification-tool |
| 13 | Realm | 1-5 | 1 Not identified; 2 Partially identified; 3 Identified but not validated; 4 Validated; 5 Fully controlled | /40: 35-40 commit; 25-34 best case; <25 pipeline or disqualify. https://www.withrealm.com/blog/meddpicc |
| 14 | Attive | 0-3 | 0 not identified or N/A; 1 partially identified; 2 identified, needs validation; 3 fully identified and validated | https://attive.ai/glossary/meddic-scoring |
| 15 | Futureman / Coffee / Iris CRM picklists | 3-state | "Not identified / In progress / Confirmed"; "Defined / Rough / Not defined"; "strong / weak / unknown" | https://futuremanlabs.com/blog/track-meddic-in-crm-without-going-stale |
| 16 | pulserevops [T4] | 0/0.5/1 per letter (/6) and 0-3 (/24) | commit >= 18 "only if both EB and Champion score at least 2" | quoted for the gating idea only. https://pulserevops.com/sales-trainings/st229 |
| 17 | Ebsta (platform) | per-criterion confidence score plus notes; "qualification score" | 2023: only 5% of companies "used a more advanced approach, scoring the confidence of each qualifying criteria" | 2025: only 36% of deals passing Discovery had both a score and notes. |

Convergent design principles across the scales:
1. The scale measures evidence quality, not deal sentiment: unknown -> rep-assumed -> buyer-confirmed -> validated by a second source, artefact or action.
2. Evidence must be attached (quote, timestamp, document) for any score above the assumed level.
3. Shape beats total: zeros on EB, Champion, Paper Process or Decision Process override a high sum.
4. Scores are expected to rise through the cycle; early low scores are normal and should not be penalised per se.
5. Scores gate forecast category (pipeline / upside or best case / commit), not just stage.

---

## 4. Deal-level rollups, qualifying out, reviews, and what predicts wins

### 4.1 How scorecards compute deal health
- Simple sum (0-24, 0-16, 0-40) with bands (section 3). Weighted variants put more weight on M, E, I, C.
- Gating rules: minimum per-element scores by stage (rework, claudeskills, Whyte at Poq); commit requires EB and Champion above a floor; "Any deal with a 0 on Economic Buyer or Champion shouldn't be in your commit forecast. Period." https://prospeo.io/s/meddpicc-sales
- Direction of travel: MEDDIC Academy and Andy Whyte both stress that the score should rise as the cycle progresses and that reviewers compare the score to the deal's stage and age, not to an absolute. Ebsta 2025: closed-won deals were only 58% complete at Discovery but 85% at Closing, so "the best sellers qualify continuously".
- Evidence-vs-assertion is the deciding distinction: "A deal scoring 8/8 on evidence is fundamentally different from a deal where the rep filled in all eight fields with assumptions." https://www.ampup.ai/resources/pipeline-review-meeting-template

### 4.2 What "qualified out" means
- Whyte's mantra: "Nobody ever regrets qualifying out." Qualifying out is a deliberate decision to stop investing in an opportunity when the evidence says it cannot be won (or won profitably), taken early. Decision Criteria "works in both directions. Use it to lock in the right deals and qualify out of the wrong ones early." https://meddicc.com/meddicc-media/medmen-3d-decision-criteria
- MEDDIC Academy teaches "SAY NO To Qualify & To Close" as a module and lists "Qualify the deal out in some cases" as a purpose of the score calculator; its founder argues that of two equally skilled reps "the one who is qualifying better is the one who will have a higher win rate by definition, because they are working on the deals which close". https://trainings.meddic.academy/courses/Advanced-MEDDIC-MEDDPICC ; https://meddic.academy/everything-you-ever-wanted-to-know-about-meddic-meddpicc-and-never-dared-ask/
- Force Management: MEDDICC "enables your sales team to quickly qualify deals in or out, so sellers can focus on accounts with the highest potential"; Kaplan's x-ray analogy: "It tells you where you're hurt (where your deals have gaps), but it doesn't tell you how to fix them."
- Operational forms: Backdrop "0-9: do not forecast it"; Closing Foundry red band "disqualify or restart discovery"; Knowlee "Walk Away does not mean the opportunity is dead, it means it needs to be reset, not forecasted"; Prospeo/MentorGroup rule "No mutual next step plus no activity in 14 days? That's not a deal. Park it with re-entry triggers."
- Data: Ebsta 2024: top performers are "366% more likely to close an opportunity at the Discovery stage" (i.e. disqualify early) and manage nearly 2x more pipeline by disqualifying faster (2025); "Top performers are 24% more likely to disqualify non-ICP deals early" (2025).

### 4.3 Use in deal reviews, pipeline reviews and forecasts
- Cadence split most guides recommend: weekly manager 1:1 deal review (30-45 min, 3-5 deals), weekly team pipeline review (30-60 min, evidence-scored), monthly forecast/business review, quarterly QBR; keep "progress deals" (pipeline) separate from "predict outcomes" (forecast). https://prospeo.io/s/deal-reviews ; https://prospeo.io/s/sales-operating-rhythm ; https://resources.rework.com/guides/sales-process/sales-operating-cadence
- Review questions that operationalise the letters (Prospeo): Metrics "Show me the buyer's target numbers, not ours"; EB "Have you spoken directly with the EB?"; Criteria "top three requirements, ranked, where are we weak?"; Process "map the steps from today to signed contract"; Paper "When's the last time something moved on procurement? If more than 7 days, what's the blocker?"; Champion "What has your Champion done for us this week, not said, done?"; Competition "Who else is in the deal? What's their strongest argument against us?" Every review ends with three actions, owners and dates.
- Three-question loop (AmpUp): exit criteria met with evidence? which elements are evidence vs assertion? what changed since last week and what is "next-next"?
- The "Three Whys / Why change, Why now, Why us, Why staff" framing maps onto the letters: Pain = why change; Champion + EB = why now; Criteria + Process = why us; Paper + Competition = "why staff" (Coommit). https://coommit.com/blog/deal-review-meeting-2026-meddpicc-ai-playbook
- Forecast-category gates: Commit = complete evidence (Nimitai >= 18; CRO Expert >= 14/16; Realm >= 35/40); Best Case / Upside = mid bands; Pipeline = everything else. Verify high scores against recordings ("any score above 3.0 must have a corresponding Gong timestamp", pulserevops template, [T4] but consistent with Prolifiq's "audit scores against the captured notes").
- Manager behaviour is the failure point: "Frameworks die when managers run deal reviews conversationally, asking what happened this week instead of what's your economic buyer engagement status and what did your champion do in the last 7 days" (CRO Expert). Coaching ratio suggestion [T4]: 3-5 unprompted framework references per 30-minute review.

### 4.4 Which elements are most predictive (published data, with caveats)

| Claim | Source | Notes |
|---|---|---|
| Fully qualified deals win 6.3x more often (50% vs 8%), close 21.6% faster (71 vs 91 days), 1.9x less likely to slip | Ebsta 2025 Qualification Report, 655k opps, 387 companies, $48B | [T2] correlation; well-qualified deals may simply be better deals |
| Only 36% of deals passing Discovery had both a score and notes; EB, Decision Process, Paper Process most often incomplete | Ebsta 2025 | [T2] |
| Decision makers active in first two stages: +55% win rate; DM engagement score > 40 throughout: win rate "quadruples" / +400% | Ebsta 2025 GTM Benchmarks | [T2]. Note: the "delayed engagement reduces win rates by 113%" line repeated by Salesmotion, Coffee and others is a misreading; the 113% figure in the report is "When late-stage deals slip beyond two months, win rates drop 113%". |
| MEDDPICC completed by Solution Presented: 324% more likely to win; 5.6 meetings and 5.2 contacts to reach >80% MEDDPICC; top performers 361% more likely to complete; 75% of closed-won had MEDDPICC completed; 68% of deals moved past qualification not qualified effectively | Ebsta 2024 (4.2M opps, 530 companies, $54B) and H1 2024 update | [T2] |
| EB raises ROI after Solution Presented: -79% likelihood of closing; top performers 241% more likely to have EB engaged before Solution Presented | Ebsta 2024 | [T2] |
| Fully utilised MEDDPICC: +311% win rates; high performers 437% more likely to complete criteria; Metrics + Decision Criteria + Paper Process least populated but +206% together; two criteria done by end of stage 2: +71% close likelihood; only 15% of opps fully qualified; 5% of companies score per-criterion confidence | Ebsta 2023 (3.2M opps) | [T2] |
| MEDDPICC without Metrics, EB, DC at stage 2: -31% win rate; Metrics + DC qualified: +37% | Ebsta INBOUND 2023 deck | [T2] |
| No DM on meetings: -80% (enterprise -233%); competitor mentioned early: +49%; closed-won has 2x buyer contacts; multi-threading +130% in $50k+ deals; DM as approver beats DM as evaluator | Gong Labs (9k to 1.8M opps) | [T2] |
| Champion is "the most predictive element"; "the Champion test is still the single most predictive question" | Salesmotion, skipcall, AmpUp | [T3] opinion, no dataset |
| "Deals with 3+ MEDDIC fields completed close at 2.1x the rate of deals with 0-1 fields" (attributed to a Gong 2027 report) | pulserevops | [T4] fabricated-looking citation; not found on gong.io |

Interpretation for the rubric: the elements that most separate top from low performers in Ebsta's usage table are Economic Buyer (85% vs 8%), Decision Criteria (76% vs 12.5%), Metrics (54% vs 9%) and Champion (56% vs 15%); Identify Pain barely separates (78% vs 66%). The elements most often missing late in the cycle (EB, Decision Process, Paper Process) are the slippage drivers. A rubric should therefore weight or gate on EB, Champion, Decision Process and Paper Process, and treat Pain identification alone as a low bar.

### 4.5 Critiques of MEDDPICC as a rollup
- Winning by Design: MEDDIC "focuses primarily on closing the deal" and "provides less guidance for what happens after"; "Recent updates with derivatives such as MEDDPIC (Paperwork) and MEDDICC (Competition) add an even greater focus on closing"; SPICED adds Impact (rational and emotional) and a dated Critical Event. https://winningbydesign.com/resources/blog/what-is-missing-from-meddic/ ; https://winningbydesign.com/resources/blog/meddic-and-spiced-2023-two-different-approaches-2/
- Keenan (Gap Selling): "80% of the sale happens in the first 2 decisions, why should I change, and why now? MEDDPICC leans heavily on Decision 3." https://salesmotion.io/blog/meddpicc-sales-methodology
- Kaplan: MEDDICC is an x-ray, not treatment; it needs a sales process and a value message (Command of the Message) around it.
- Practical implication: add a "critical event / compelling event" field alongside Decision Process, and record the buyer's emotional as well as economic impact under Pain.

---

## 5. Measuring adoption after training

### 5.1 The measurement problem
- Compliance theatre: "You can report that 94% of opportunities have all MEDDPICC fields populated. You cannot easily report that 94% of those fields contain useful information." (AmpUp). "The moment you tell a team that 90% of opportunities need all MEDDPICC fields completed, you'll get 90% completion and 80% garbage data" (CRO Report). https://www.ampup.ai/resources/meddpicc-sales-methodology-coaching-guide ; https://thecroreport.com/blog/implement-meddpicc/
- Fields without evidence: "A Champion can be marked, and the Paper Process can be flagged as known after a single mention in a vague email. These fields become checkboxes because the system doesn't challenge them." (SalesMethods) https://salesmethods.com/blog/how-to-get-your-sales-team-to-use-meddpicc/
- Decay timeline observed by Demodesk: weeks 1-2 energy high; weeks 3-4 reps skip EB and Decision Process; weeks 5-8 manager scoring diverges ("Manager A weighs Economic Buyer heavily, Manager B focuses on Metrics"); weeks 9-12 usage collapses to whatever CRM required fields enforce. https://demodesk.com/blog/meddicc-framework-implementation-enablement-timeline
- "Fields get filled the night before the forecast call, from memory" (Weflow) and reconstructed memory "rewrites the history of the conversation to match what they wish had happened" (Backdrop). https://www.weflow.ai/blog/meddic-fields-blank-in-gong ; https://www.getbackdrop.ai/blog/meddpicc-rollout-salesforce-trap

### 5.2 Kirkpatrick framing (Level 3 = behaviour on the job)
- Level 3 "is the most important Kirkpatrick level"; define observable on-the-job behaviours, build support and accountability systems, have managers inspect weekly; "training people and hoping for the best typically results in success less than one-third of the time". https://www.kirkpatrickpartners.com/blog/integrating-technology-with-the-kirkpatrick-model-for-enhanced-training-evaluation/
- Measure at 30, 60 and 90 days against a pre-training baseline on the same reps; combine self-report with an observable source (manager rubric, call-recording audit, CRM events); report matched-sample size and reversion rate. https://www.sopact.com/use-case/behavior-change-after-training ; https://trainercentric.in/kirkpatrick-model/
- Data-join pattern: LMS user_id to CRM owner_id; compare stage duration, win rate and deal size for trained vs untrained cohorts; anonymised example: 120 AEs trained on a discovery framework, early-stage duration 18 to 13 days, qualified-deal win rate 24% to 29% within 90 days. https://www.continuous-learning.net/kirkpatrick-model-examples-five-corporate-programs-that-actually-measured-behavior-change

### 5.3 Adoption metrics practitioners actually use
Leading (behavioural) indicators:
- Percentage of Stage 3+ deals with a named, engaged EB and a documented Decision Process; "When that number crosses 80%, the framework is working" (CRO Expert). Percentage of Stage 4 deals with Paper Process timeline confirmed.
- Per-element evidence coverage on recorded calls (Gong initiative boards: adoption thresholds green > 70%, red < 40%, by team and element). https://www.gong.io/blog/gong-on-gong-strategic-enablement-initiatives
- Scoring variance: manager scores vs AI scores should converge (Demodesk); Ebsta 2023 noted only 5% of companies score confidence per criterion.
- Unprompted framework language in deal reviews (coaching ratio) and rep-initiated use ("public recognition when reps credit the framework for a win").
- Time-to-disqualification for deals missing EB or Pain; stage-advancement rate for deals with a verified vs assumed Champion (AmpUp "measure execution quality, not CRM completeness").
- 60-day pulse survey: "how much does the methodology help you win" (>6/10) vs "slow you down" (<4/10). [T4 but sensible]
Lagging indicators:
- Win rate on deals with complete-and-evidenced MEDDPICC vs incomplete ("the most telling metric", CRO Report); average score of closed-won vs closed-lost (ziellab suggests a gap of 20+ points on a 100 scale; pulserevops 0.5 on a 6-point scale).
- Forecast accuracy (commit vs actual), slippage rate, cycle length, average deal size.
- MEDDICC maturity model (meddpicc-measure.com): from "CRM fields filled after the fact" and "success measured by outcomes only" to "execution quality metrics: element coverage, risk accuracy", "continuous tracking of EB access, M2 coverage", quarterly win/loss/slip reviews. https://meddpicc-measure.com/
- Ebsta's own recommendation: "reinforcing MEDDPICC or similar methodologies across all stages, not just early discovery, and using qualification rigor as a leading indicator for forecasting health and coaching effectiveness". https://www.ebsta.com/news-updates/new-ebsta-report-sales-qualification/

### 5.4 Published before/after and correlation numbers (with vendor-marketing flags)

| Claim | Source | Flag |
|---|---|---|
| Indico Data: conversion +50%, average deal size +140% (3x ACV), time to close -25%, new business +33% | MEDDICC Ltd customer story https://meddicc.com/customer-stories/indico-data | vendor case study, no baseline detail |
| PE-backed B2B org: win rate 23% to 46%, forecast accuracy 25% to 85%, quota attainment to 83%, ACV $50k to $81k | MEDDICC Ltd case via casestudies.com | vendor case study |
| Intercom: "average revenue per account has increased almost 4x" after Command of the Message + MEDDPICC | Force Management offerings page | testimonial |
| Quick Channel (Sweden): bigger deals, shorter cycles, higher mid-market close rate after nine months of MEDDPICC in HubSpot | MEDDICC.se | vendor, no numbers |
| Logistics company: win rate +23% after MEDDPICC with per-criterion scoring in weekly pipeline reviews | Ebsta 2023 report p.12 | vendor spotlight |
| "Full adopters report 18% higher win rates and 24% larger deal sizes"; "73% of SaaS companies selling above $100K ARR use some version" | Salesmotion, Saber, umbrex, AmpUp, skipcall (attributed variously to Sales Assembly, Force Management 2025, or nobody) | [T4] circular; no primary source found. Do not cite as evidence. |
| "Teams with 90%+ coverage reach 61% win rates, low coverage 17%" | coffee.ai table citing "Scratchpad Analysis", "Forecastio Study" | [T4] unverifiable |
| Korn Ferry: best-in-class orgs with formal or dynamic process have 26% higher win rates and 21% higher quota attainment; consistent coaching and impact measurement: 32% higher win rates, 28% higher quota attainment; coaching cultures: +14% quota, +15% win rate, ~20% lower turnover; methodology with data-driven insights: +28% win rate | Korn Ferry Sales Maturity / Sales Enablement studies https://www.kornferry.com/insights/featured-topics/sales-transformation/building-the-business-case-for-sales-coaching ; https://www.kornferry.com/insights/talent-suite-resources/missing-sales-targets-need-sales-coaching | [T2] survey-based, self-reported |
| Pavilion x MetaCX "State of Sales Methodologies in B2B SaaS" (400 sales leaders) | https://www.joinpavilion.com/resource/the-state-of-sales-methodologies-in-b2b-saas | gated; numbers not public |
| "MEDDPICC appears in 18.4% of VP+ requirements" | CRO Report inline quote | inconsistent with its own 9.0% table |
| Behavioural adoption takes 60-90 days (CRO Expert), 3 months to feel natural and 6 to lock in (AmpUp), 2-3 quarters (Sales Assembly via ziellab), 12-18 months for full fluency (skipcall); "44% of methodology adoptions abandoned within 18 months" (CSO Insights via smartsales.ai) | practitioner estimates | [T3] |

---

## 6. Pedagogy relevant to coaching design

### 6.1 Conscious competence
- Provenance: four-stage model appears in a 1960 NYU management textbook, Martin Broadwell's 1969 "four levels of teaching", Curtiss and Warren (1973), and was popularised by Noel Burch at Gordon Training International in the 1970s as "the four stages for learning any new skill" (unconsciously unskilled, consciously unskilled, consciously skilled, unconsciously skilled). Often misattributed to Maslow. https://en.wikipedia.org/wiki/Four_stages_of_competence ; https://www.gordontraining.com/leadership/four-stages-learning-theyre-circle-not-straight-line/ ; https://www.mindtools.com/ah651dp/the-conscious-competence-ladder/
- Stage 3 is defined as: can perform reliably at will, needs concentration, "if it is broken, they lapse into incompetence", can demonstrate but not yet teach; practice is the move from 3 to 4. https://globalioc.com/wp-content/uploads/2018/05/Conscious-Competence-Learning-Model-RCC-Mod-4.pdf
- Sales-enablement use: diagnose each rep's stage per skill and coach accordingly. Stage 1 needs awareness (play their own call back); Stage 2 needs structure and psychological safety (one behaviour, one practice, one checkpoint); Stage 3 needs "reps and reinforcement" because reps "regress here under stress"; Stage 4 needs new challenges and teaching others, plus guarding against complacency. "Most managers coach every rep the same way, usually with a Stage 3 script." https://nimitai.com/blog/sales-coaching-complete-guide ; https://jiminny.com/blog/the-4-stages-of-competence ; https://www.fullfunnel.co/blog/timing-is-everything-in-sales-training ; https://www.gregmartinelli.net/the-most-competent-salesperson-in-the-market/
- Membrain's warning that maps to MEDDPICC rollouts: "As much as 87% of what we learn is forgotten if we don't go through stages 3 to 4... there will be no results without practice and reinforcement." https://www.membrain.com/blog/the-ladder-of-sales-competence
- Gordon Training's own point: the stages are "a circle, not a straight line"; every new context (new segment, new product, new objection) sends a Stage 4 rep back to Stage 2 or 3.

### 6.2 Forgetting, spacing, retrieval
- The "87% forgotten within 30 days" figure is attributed variously to Research Institute of America, CSO Insights, ATD citing Gartner ("roughly 70% within a week, 87% within a month"); treat the exact number as folklore, the direction as robust. https://blog.sendspark.com/sales-training-and-coaching ; https://talsmart.com/blog/sales-training-forgotten/ ; https://www.grindhotline.com/sales-training-doesnt-fail-your-follow-through-does.html
- Primary research: Ebbinghaus (1885) forgetting curve; Cepeda et al. 2006 meta-analysis of 254 studies on the spacing effect; Roediger and Karpicke 2006 on the testing effect (retrieval beats restudy). Applied: three half-hour weekly sessions beat one three-hour workshop on identical content; a weekly coaching session is a retrieval event. https://www.supered.io/blog/sales-coaching-plan/
- Spaced repetition in sales enablement claims 30-55% better recall than single-event learning (Allego). https://www.allego.com/blog/spaced-repetition-is-the-key-to-sales-training-reinforcement/
- Reinforcement design consensus: start within 24-48 hours; tight interval (every 2-3 days) for two weeks, then weekly, then biweekly; scenario-based production of the behaviour, not re-reading; 8-12 logged practice reps in the first 30 days; a 90-day programme with gates at days 14, 45 and 90; second-line leaders inspect whether first-line cadence is happening because "cadences decay from the top down". [T4 synthesis but consistent with the primary research] https://pulserevops.com/knowledge/q461 ; example cadence Day 0 workshop, Day 2 quiz, Day 7 role-play, Day 14 real call review, Day 30 certification refresh. https://prospeo.io/s/sales-training-tips

### 6.3 Coaching cadence and dose
- Operating rhythm layers: daily stand-up (10-15 min, blockers only, not deal review); weekly 1:1 (30-45 min, coaching not status; Gartner via rework: managers who spend at least 50% of 1:1 time on skill coaching produce 23% higher quota attainment); weekly pipeline review (30-60 min, evidence-scored); monthly business review (60-90 min, trends and coaching priorities); quarterly QBR (half day, decisions). Collapsing them into one meeting loses the purpose of the others (Kazanjy). https://resources.rework.com/guides/sales-process/sales-operating-cadence ; https://allstonlabs.com/library/scaling-the-team/operating-rhythm ; https://www.antoinebuteau.com/sales-management-series-3-the-sales-manager-operating-cadence/
- Dose: Korn Ferry / CSO Insights: coaching pays from about three hours per rep per month, run weekly, flattening past roughly five; reps under managers delivering 3+ hours/month hit quota at ~94% vs ~84% at 2 hours (widely quoted secondary figures). Korn Ferry: formal or dynamic coaching linked to 32% higher win rates, 28% more reps at quota; "you can form or break a pattern of behavior in about 21 days". https://www.kornferry.com/insights/featured-topics/sales-transformation/three-levers-that-drive-sales-performance ; https://www.kornferry.com/insights/featured-topics/sales-transformation/5-steps-to-a-powerful-sales-coaching-program
- Separate skill coaching from deal inspection: "When skill coaching and deal inspection share a meeting, the urgent always eats the important."
- Manager coverage reality: managers listen to "fewer than 5%" (AmpUp) or "less than 1%" (Hyperbound) of recorded calls, which is the main argument for automated scoring.

### 6.4 Does AI scoring undermine conscious competence? Both sides

The case that it does:
- Cognitive offloading and skills atrophy: Imparta argues that letting AI handle objection responses, follow-ups and negotiation prep erodes recall and in-the-moment thinking; "high confidence in AI suppresses users' critical thinking"; a self-reinforcing loop (skills atrophy, self-confidence falls, reliance grows). Recommends "pull mode" AI that asks questions and structures the seller's thinking, "a coach, not a crutch". https://imparta.com/resources/when-ai-thinks-for-you-the-impact-of-skills-atrophy-and-cognitive-offloading-on-sales-performance/
- Primary research behind it: Lee et al., CHI 2025 (319 knowledge workers, 936 examples): confidence in GenAI negatively correlates with enacted critical thinking (beta = -0.69, p < 0.001); self-confidence in doing the task (+0.26) and in evaluating AI output (+0.31) correlate positively; GenAI shifts critical thinking toward verification and stewardship; barriers are awareness, motivation, ability. https://www.microsoft.com/en-us/research/publication/the-impact-of-generative-ai-on-critical-thinking-self-reported-reductions-in-cognitive-effort-and-confidence-effects-from-a-survey-of-knowledge-workers/ . Gerlich 2025 (Societies 15(1):6): negative correlation between frequent AI tool use and critical thinking, mediated by cognitive offloading, strongest in younger users. https://doi.org/10.3390/soc15010006 . A 2025 position paper distinguishes "performed" (unaided) from "demonstrated" (AI-assisted) critical thinking and notes most evaluations only measure the latter. https://arxiv.org/html/2504.14689v1
- Applied to sellers: "AI doing the homework doesn't make you smarter. It just means the homework gets done"; sellers "can produce a flawless account brief in 90 seconds, yet can't answer a basic question about their customer's business" (Morrissey). https://www.linkedin.com/pulse/ai-making-enterprise-sellers-worse-heres-why-patrick-morrissey-rm1bc
- Real-time prompting specifically: reps become "cognitively split", buyers detect it, and "real-time coaching can become a crutch... take the tool away... and the gap is enormous"; post-call analysis "changes how someone communicates" because the rep owns the improvement. https://medium.com/@RonaldSkeltonJr/the-real-time-coaching-trap-why-your-ai-is-teaching-reps-to-sound-less-human-22bffae817b7
- Silent auto-fill: "A tool that silently fills everything removes the reflection the methodology existed to force. That's a real tension, not a marketing objection" (Weflow, itself an auto-fill vendor). Organisational version: when top-performer judgement is captured into an agent and humans stop practising the hard cases, "the knowledge freezes... no one knows how to update the thinking behind it" (Steffen). https://caiosteffen.com.br/en/blog/o-agente-aprendeu-os-vendedores-esqueceram
- Enforcement without enablement: "You can't extract what was never said"; AI capture "hides" the discovery skill gap rather than fixing it; "enforcement without enablement is just a more sophisticated way of auditing incompetence" (Hyperbound). https://www.hyperbound.ai/blog/meddpicc-crm-native-vs-ai

The counter-argument (AI scoring can strengthen conscious competence if designed as feedback, not substitution):
- The conscious-competence model itself says Stage 1 reps need awareness they cannot generate alone; recorded-call scoring is the mirror ("holding up the mirror" is one of the two components of coaching, Martinelli). Stage 3 reps need many repetitions with feedback; 100% call coverage supplies feedback at a volume managers cannot (AmpUp, Jiminny: "conversation intelligence takes the guesswork out of coaching").
- Learning science supports scoring as a retrieval and feedback event when the rep is made to answer first: "auto-fill plus a human loop. The machine computes from the evidence, the rep still answers the question, and the gap between the two is the coaching moment" (Weflow). Propose-confirm-reject with a required reason for overrides keeps the rep's judgement in the loop (pulserevops [T4], Weflow, Oliv: "Do not over-automate by removing all manual override capability... do not use auto-scores as punitive metrics. They are coaching inputs, not performance grades.").
- Lee et al.'s own design recommendations: tools should raise awareness, motivation and ability for critical thinking, provide reasoning explanations, guided critiques and cross-references, and act as "a thought partner, one that can also act as a provocateur". A judge that shows its evidence and its reasoning, and asks the rep what it missed, fits this.
- Closed loop of score real calls -> diagnose element gap -> practise (role-play) -> score again (Hyperbound; Vanta claim of ramp 210 to 72 days is vendor-reported).
- Post-call rather than in-call is the safer default for skill building; in-call prompting should be transparent to the buyer if used at all (Skelton).

Design principle that reconciles both: the LLM judge should score evidence in the conversation, not replace the rep's qualification act. Reps self-score first (retrieval), the judge scores independently (feedback), disagreements are surfaced with quotes (awareness), and the coaching cadence turns repeated gaps into practice (reinforcement). Never silently write scores to the system of record.

---

## 7. Implications for an LLM judge (design notes before the rubric)

1. Score evidence, not sentiment. Every score above 1 must cite a verbatim buyer quote, a buyer artefact, or an observed buyer action, with speaker attribution and timestamp/source. "No quote = score of 0" is the single rule practitioners say kills "MEDDPICC theatre".
2. Separate who said it. Rep assertion ("the CFO is the EB") is worth at most 1. Buyer statement is 2. Buyer statement corroborated by a second buyer-side person, a document, or a demonstrated action is 3.
3. Mention is not validation. "CFO was discussed" is not "CFO has budget authority and agreed to sponsor" (Oliv). Trackers detect topics; the judge must decide whether the criterion was confirmed.
4. Score per interaction, accumulate per deal. Qualification is cumulative across calls and emails; a single call should be judged on what it added or contradicted, with the deal-level score as a max-with-decay over sources (a champion "validated" 90 days ago with no action since should decay).
5. Stage-aware expectations. Do not penalise absent Paper Process in a first discovery call; do flag it as a gap for a Stage 3+ deal. Backdrop's warning: "most deals have three or four zeros" early and that is honest.
6. Known extraction failure modes to guard against (from pulserevops [T4], Weflow, Oliv, all consistent with practitioner canon): coach scored as champion; status quo missed because no vendor named; EB chosen by title; pain intensity overstated from "yeah, that's annoying"; contradicting statements across calls collapsed to "whichever arrived last".
7. Output for coaching, not policing: per element give what we know (buyer's words), the score, why not one higher, and the single question that would raise it (Backdrop prompt pattern). Present as a proposal the rep confirms, edits or rejects with a reason.
8. Keep the shape visible: report the vector, not only the sum; flag zeros on EB, Champion, Decision Process and Paper Process regardless of total.

---

## 8. Proposed rubric v0

### 8.1 Scoring rules (apply to every element)

Evidence ladder (0-3), synthesised from Backdrop, Prolifiq, Tech Sales Playbook, rework and Whyte's criteria-per-level principle:
- 0 Unknown: no one on the deal can answer the element's question; nothing in the interaction addresses it.
- 1 Asserted / inferred: the rep states or infers it; the buyer has not said it, or said something too vague to count. Also the ceiling when the only source is an org chart, a title, or the rep's own ROI model.
- 2 Buyer-stated: the buyer said it, on a call or in writing, specifically enough to act on; single source.
- 3 Buyer-validated: confirmed by a second buyer-side person, a buyer-produced artefact (scorecard, procurement doc, email), or a demonstrated buyer action (meeting booked, questionnaire sent, business case circulated); and connected to the decision.

Mandatory fields per element per interaction: score; evidence (verbatim quote with speaker and timestamp, or artefact reference); why-not-higher; next question; confidence (high/medium/low) for the judge's own extraction.

Deal-level: element score = maximum across interactions, decayed one level if the latest supporting evidence is older than one full stage or 45 days (whichever shorter) and no reinforcing evidence has appeared; contradictions (buyer later reverses) reset to the latest evidence level.

Stage expectations (for gap flags, not penalties): Discovery: I, M, C(hampion) >= 2 expected; Evaluation: + E, DC >= 2, DP >= 1; Proposal: E >= 2 met, DP >= 2, PP >= 1, Comp >= 2; Negotiation/Commit: all >= 2, E and C(hampion) >= 3, PP >= 2.

### 8.2 Per-element anchors and example evidence

Example quotes are illustrative, written for this document, not sourced.

M Metrics
- 0: no quantified outcome anywhere.
- 1: rep-supplied number or generic benchmark. Rep: "Customers like you typically save 30% on reporting time."
- 2: buyer states a number with baseline and target, one source. Buyer: "Month-end close takes us 11 days; we need it under 5 by the next audit."
- 3: number validated by the EB or a second stakeholder, tied to a KPI they own, with a date. EB: "If this gets close to five days, that's the KPI I'm reporting to the board in Q2; finance has confirmed the 11-day baseline."
- Next question at 1: "What number moves if this works, and who reports it?"

E Economic Buyer
- 0: not identified.
- 1: named by title or inference; not met; no path. Rep note: "Probably the CFO."
- 2: buyer names the person and their authority; meeting requested or planned. Buyer: "Priya signs anything over 100k; she'd want to see the business case before procurement."
- 3: EB met; EB confirmed priority, funds and timeline; or Champion has booked the EB meeting and the EB has engaged (email reply, calendar acceptance). EB: "I can reallocate from the analytics line if the payback is inside two quarters."
- Next question at 1: "How does a decision of this size get made here, and who signs the actual contract?"

DC Decision Criteria
- 0: none stated.
- 1: generic list or rep's assumption. Buyer: "Integrations, price, support."
- 2: specific criteria in the buyer's words, one stakeholder, may be inherited from an RFP. Buyer: "Must cover raw tables, not just modelled ones, and must not require my team to write more tests."
- 3: criteria weighted, documented (scorecard, RFP), covering technical, economic and relationship dimensions, confirmed by more than one stakeholder, and including at least one criterion the rep shaped. Buyer: "We added 'no new test burden' to the evaluation sheet after your session; it's weighted 30%."
- Next question at 1: "If you wrote the evaluation scorecard today, what are the rows and how are they weighted?"

DP Decision Process
- 0: unknown.
- 1: timeline only, or process inferred from a previous purchase. Buyer: "Hopefully this quarter."
- 2: steps and participants named by the buyer; some dates missing. Buyer: "Technical session, then security review, then the procurement committee, which meets the first Monday each month."
- 3: steps, owners and dates confirmed, tested against a second source, and a critical event named; mutual plan agreed. Buyer: "Steering is on the 14th; the CFO wants a decision before the fiscal-year lock on the 30th; here's the plan back from your side."
- Next question at 1: "Walk me from today to the day we'd sign: steps, who approves, and roughly when?"

PP Paper Process
- 0: not discussed (acceptable in early discovery; flag from Evaluation onwards).
- 1: acknowledged without detail. Buyer: "Legal will need to look at it."
- 2: owners and typical durations stated by the buyer; questionnaire or MSA path identified. Buyer: "Security review is Tom's team, usually six weeks; we'll want our MSA."
- 3: steps in motion or precisely mapped with dates and owners, security questionnaire received or cleared, vendor onboarding started. Buyer (email): "Attached is the vendor questionnaire; procurement opened a ticket; redlines back by the 20th."
- Next question at 1: "Walk me through the last vendor you onboarded: who was involved and how long did each step take?"

I Pain (Identify / Indicate / Implicate)
- 0: no problem named.
- 1: rep names the pain; buyer only acknowledges. Buyer: "Yeah, reporting is a bit slow."
- 2: buyer states the pain in their own words, qualitatively, with an owner. Buyer: "Every month we're scrambling to get the board pack out; it's my team that takes the heat."
- 3: buyer quantifies impact, names the consequence of inaction, ties it to a date or event, and connects it to a personal or organisational stake. Buyer: "Two analyst days per incident, twice a month; last time we missed the board deadline the CFO called it out in the all-hands."
- Next question at 1: "What happens if this is still the case in six months?"

C Champion
- 0: no advocate identified.
- 1: friendly, responsive contact; no test passed; or contact lacks power. Rep note: "VP Data is keen and replies quickly."
- 2: one test passed with evidence: an introduction made, an internal doc shared, or explicit statement of personal stake. Buyer: "I've been told to fix this by year end; my bonus is tied to close time."
- 3: repeated internal selling observed: booked the EB meeting, presented the case in a meeting the rep was not in, defended against pushback, volunteers intel unprompted, and has stated personal win. Champion (email): "Presented your ROI to Priya and the ops leads yesterday; ops pushed on migration risk; I used the reference call notes. She wants a 20-minute call with you Thursday."
- Next question at 1: "Who else needs to be in the room for the next conversation, and can you set that up by Friday?"

C Competition
- 0: unknown.
- 1: alternatives guessed by the rep, or buyer says "just you".
- 2: buyer names alternatives (vendors, build, do nothing) but not where each is stronger. Buyer: "We're also looking at our BI vendor's module and hiring two engineers."
- 3: buyer states each alternative's strengths and weaknesses, the status quo has been explicitly tested and the buyer has stated why doing nothing is not acceptable, and the criteria reflect the rep's differentiation. Buyer: "The bundled module can't cover raw tables, hiring takes six months we don't have, and doing nothing means another missed board pack."
- Next question at 1: "If you did nothing for another two quarters, what would happen?"

Optional ninth field recommended by the SPICED critique: Critical Event (date-bound reason in the buyer's world), scored 0 none / 1 rep-supplied deadline / 2 buyer-stated event / 3 buyer-stated event with consequence and named owner.

### 8.3 Per-interaction outputs (what the judge emits for one call, email or note)
- Element vector (8 or 9 scores), evidence objects, why-not-higher, next question, extraction confidence.
- Delta vs prior deal state: elements raised, lowered, contradicted.
- Behaviour flags on the rep: asked at least one question per expected element for the stage; asked an implicating question after a pain statement; asked a champion test question; asked for EB access; asked a paper-process question at or after Evaluation; did not knock competitors; secured a mutual, dated next step.
- Hygiene flags: rep monologue ratio, pitch-before-pain, checklist interrogation (more than N consecutive closed questions).

### 8.4 Deal-level metrics computable from per-interaction scores
- MEDDPICC total (0-24) and band; element vector; count of zeros; count of elements at 3.
- Gate status: commit-eligible (all >= 2, E and Champion >= 3, PP >= 2), upside, pipeline, qualify-out candidate (total <= 9 after N interactions, or E or Champion still 0 after Evaluation).
- Evidence quality index: share of element scores backed by buyer quotes or artefacts vs rep assertions.
- Freshness: days since last reinforcing evidence per element; decayed elements list.
- Score trajectory: total per interaction over time; interactions-to-80% (benchmark: Ebsta 5.6 meetings, 5.2 contacts).
- Stage-expectation gaps: elements below the expected level for the current stage.
- Stakeholder coverage: distinct buyer-side people with evidence attached (multi-threading proxy); EB engaged before Solution Presented (yes/no); champion action count.
- Contradiction count: buyer statements that reverse earlier evidence.
- Critical event present and dated (yes/no).

### 8.5 Rep-level metrics (adoption and skill, aggregated across the rep's interactions and deals)
- Element coverage rate: share of interactions at each stage where the rep asked at least one question for each stage-expected element (per element, per stage).
- Evidence rate: share of the rep's element scores at 2+ that are buyer-sourced vs rep-asserted (the "1 vs 2" discipline).
- Champion test rate: share of deals past Evaluation where at least one champion test was asked and one champion action was observed.
- EB access rate: share of Stage 3+ deals with E >= 2; share with E = 3 before proposal.
- Paper-process timing: stage at which PP first reached 1 (target: Evaluation, not Negotiation).
- Implication rate: share of pain statements followed by an implicating question within the same interaction.
- Self-score vs judge-score variance: mean absolute difference and direction (happy-ears index); trend over time.
- Override behaviour: share of judge proposals accepted, edited, rejected, with reasons logged.
- Score trajectory slope: average total gained per interaction; interactions to reach 16/24.
- Disqualification behaviour: share of deals qualified out before Proposal; average total at qualify-out.
- Outcome joins (lagging): win rate and slippage for the rep's deals split by evidence-quality band; average closed-won vs closed-lost total (target gap >= 4 points on 24).
- Adoption trend (Kirkpatrick L3): coverage and evidence rates at baseline, 30, 60, 90 days post-training; reversion flag if the 60-day figure falls below the 30-day figure.

### 8.6 Guardrails
- Judge scores are proposals; the rep confirms, edits or rejects with a reason before anything is written to the system of record.
- Rep self-scores before seeing judge scores at least on a sampled basis, to preserve retrieval practice.
- No element score above 1 without an attached quote or artefact; no deal-level 3 without a second source or action.
- Calibrate against manager scores on a sample monthly; report inter-rater agreement; recalibrate anchors when agreement falls.
- Never use per-interaction scores as a comp or performance-review input directly; use them as coaching inputs and adoption telemetry.

---

## Appendix: canonical sources by section

Lineage: https://meddicc.com/resources/who-created-meddic ; https://www.salesmeddic.com/blog/origin-of-meddic ; https://meddic.academy/definition-meddic/ ; https://meddic.academy/meddic-sales-methodology-checklist/ ; https://meddpicc.net/ ; https://andywhyte.com/book/ ; https://www.forcemanagement.com/blog/meddic-vs.-meddpic-the-meaning-difference-and-benefits-of-each-for-sales-qualification-force-management ; https://www.forcemanagement.com/blog/make-meddicc-work-for-your-sales-organization ; https://www.closingfoundry.com/insights/meddic-vs-meddpicc ; https://revcentricpartners.com/blog/meddic-vs-meddpicc-origins-and-differences ; https://pulserevops.com/knowledge/q12723 [T4]

Element canon: https://meddicc.com/what-is-meddpicc/metrics ; https://meddicc.com/what-is-meddpicc/economic-buyer ; https://meddicc.com/what-is-meddpicc/decision-criteria ; https://meddicc.com/what-is-meddpicc/decision-process ; https://meddicc.com/what-is-meddpicc/paper-process ; https://meddicc.com/what-is-meddpicc/implicate-the-pain ; https://meddicc.com/what-is-meddpicc/champion ; https://meddicc.com/what-is-meddpicc/competition ; https://www.forcemanagement.com/blog/how-meddicc-helps-win-with-decision-makers ; https://www.forcemanagement.com/blog/stand-in-the-moment-of-pain ; https://www.businessfloss.com/books/the-qualified-sales-leader ; https://www.bookey.app/book/the-qualified-sales-leader ; https://www.gong.io/blog/meddic-sales-process ; https://meddicc.com/meddicc-media/medmen-s1-ep6-economic-buyer ; https://meddicc.com/meddicc-media/medmen-3d-decision-criteria

Champion tests: https://www.ampup.ai/resources/sales-champion-qualification-framework ; https://thecroreport.com/blog/meddpicc-champion/ ; https://revcentricpartners.com/blog/meddic-champion-criteria-identify-test-develop ; https://www.accountmap.ai/blog/identify-sales-champions ; https://www.meddicmondays.com/post/think-you-have-a-champion-prove-it

Question sets: https://nimitai.com/blog/meddpicc-discovery-questions ; https://prospeo.io/s/meddpicc-questions ; https://qwilr.com/blog/25-meddpicc-questions/ ; https://terasu.koromo.io/en/blog/meddpicc-sales-framework ; https://www.retorio.com/blog/meddpicc-discovery-questions ; https://prospeo.io/s/implicate-the-pain

Scoring scales: see section 3 table.

Data: https://www.ebsta.com/wp-content/uploads/2023/02/2023-B2B-Sales-Benchmark-Report.pdf ; https://www.ebsta.com/wp-content/uploads/2024/02/B2B-Sales-Benchmarks-2024_.pdf ; https://www.ebsta.com/wp-content/uploads/2024/07/H1-Update-2024-B2B-Sales-Benchmarks.pdf ; https://benchmarks.ebsta.com/hubfs/V3%202025%20Benchmark%20Report/gtm_benchmarks_digital_report.pdf ; https://www.ebsta.com/news-updates/new-ebsta-report-sales-qualification/ ; https://www.sendtrumpet.com/driving-profitable-growth-through-smarter-qualification-ebsta-x-trumpet-report-2025 ; https://www.ebsta.com/wp-content/uploads/2023/10/Ebsta-x-Sprocketeer-B2B-Sales-Benchmarks-INBOUND.pdf ; https://www.gong.io/blog/heres-how-selling-to-decision-makers-affects-your-win-rates-ignore-at-your-own-risk ; https://www.gong.io/blog/data-shows-top-reps-dont-just-sell-they-orchestrate-with-ai ; https://www.gong.io/blog/competitor-mentions-science-uncovers-how-they-influence-b2b-sales ; https://www.gong.io/blog/when-and-how-to-multi-thread-when-selling-to-executives ; https://www.gong.io/blog/gong-on-gong-strategic-enablement-initiatives

Adoption and reviews: https://www.ampup.ai/resources/meddpicc-sales-methodology-coaching-guide ; https://thecroreport.com/blog/implement-meddpicc/ ; https://cro.expert/blog/meddpicc-sales-qualification-guide ; https://demodesk.com/blog/meddicc-framework-implementation-enablement-timeline ; https://meddpicc-measure.com/ ; https://salesmethods.com/blog/how-to-get-your-sales-team-to-use-meddpicc/ ; https://www.weflow.ai/blog/meddic-fields-blank-in-gong ; https://oliv.ai/blog/meddic-auto-scoring-sales-methodology-enforcement ; https://www.hyperbound.ai/blog/meddpicc-crm-native-vs-ai ; https://www.getbackdrop.ai/blog/meddpicc-rollout-salesforce-trap ; https://prospeo.io/s/deal-reviews ; https://www.ampup.ai/resources/pipeline-review-meeting-template ; https://meddicc.com/customer-stories/indico-data ; https://www.casestudies.com/company/meddicc/case-study/building-a-high-performing-value-driven-gtm-engine-through-meddpicc ; https://thecroreport.com/blog/sales-methodology-adoption-rates/ ; https://www.kirkpatrickpartners.com/blog/integrating-technology-with-the-kirkpatrick-model-for-enhanced-training-evaluation/ ; https://www.continuous-learning.net/kirkpatrick-model-examples-five-corporate-programs-that-actually-measured-behavior-change ; https://www.sopact.com/use-case/behavior-change-after-training

Pedagogy and AI debate: https://en.wikipedia.org/wiki/Four_stages_of_competence ; https://www.gordontraining.com/leadership/four-stages-learning-theyre-circle-not-straight-line/ ; https://www.membrain.com/blog/the-ladder-of-sales-competence ; https://nimitai.com/blog/sales-coaching-complete-guide ; https://jiminny.com/blog/the-4-stages-of-competence ; https://www.supered.io/blog/sales-coaching-plan/ ; https://www.allego.com/blog/spaced-repetition-is-the-key-to-sales-training-reinforcement/ ; https://www.kornferry.com/insights/featured-topics/sales-transformation/building-the-business-case-for-sales-coaching ; https://www.kornferry.com/insights/featured-topics/sales-transformation/three-levers-that-drive-sales-performance ; https://resources.rework.com/guides/sales-process/sales-operating-cadence ; https://allstonlabs.com/library/scaling-the-team/operating-rhythm ; https://imparta.com/resources/when-ai-thinks-for-you-the-impact-of-skills-atrophy-and-cognitive-offloading-on-sales-performance/ ; https://www.microsoft.com/en-us/research/publication/the-impact-of-generative-ai-on-critical-thinking-self-reported-reductions-in-cognitive-effort-and-confidence-effects-from-a-survey-of-knowledge-workers/ ; https://doi.org/10.3390/soc15010006 ; https://arxiv.org/html/2504.14689v1 ; https://www.linkedin.com/pulse/ai-making-enterprise-sellers-worse-heres-why-patrick-morrissey-rm1bc ; https://medium.com/@RonaldSkeltonJr/the-real-time-coaching-trap-why-your-ai-is-teaching-reps-to-sound-less-human-22bffae817b7 ; https://caiosteffen.com.br/en/blog/o-agente-aprendeu-os-vendedores-esqueceram ; https://winningbydesign.com/resources/blog/what-is-missing-from-meddic/ ; https://orm-tech.com/blog/spiced-vs-meddic/
