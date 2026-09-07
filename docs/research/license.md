# Source-available licence research and draft

Date: 2026-09-07. Prepared for a source-available project with four requirements:

- (a) anyone can download, use, modify and redistribute it for free, including companies using it internally for their own sales teams
- (b) nobody may remove or obscure the project's logo, name and attribution notices
- (c) nobody may embed, bundle or offer it as part of a paid product or paid/hosted service without written permission (separate commercial licence on request)
- (d) short, well understood, does not scare enterprise sales teams

Everything below was checked against the current licence texts and policy pages fetched on 2026-09-07 (source list at the end). This is research, not legal advice: get the final draft reviewed by a lawyer in the licensor's jurisdiction before shipping it.

---

## 1. Bottom line

**Recommendation: base the licence on Elastic License 2.0 (ELv2), renamed, with two additions: a "Commercial Offering" limitation and an "Attribution Marks" clause backed by a narrow trademark permission.** Section 4 has the full draft (about 85 lines).

Why ELv2 and not FSL:

1. ELv2 already contains the notice-preservation limitation ("You may not alter, remove, or obscure any licensing, copyright, or other notices of the licensor in the software"), and Elastic's own FAQ says this covers "the terms Elasticsearch and Kibana, in-product logos, etc." That is 80 percent of requirement (b) with a five-year track record behind it. FSL only says "not remove any copyright notices".
2. ELv2 has no expiry. FSL is a Fair Source licence: every version converts to MIT or Apache-2.0 two years after release, and MIT lets anyone strip the logo. Requirement (b) is meant to be permanent, so FSL's core feature works against it.
3. ELv2's restriction sits on the right axis: how the software is provided to third parties (hosted or managed service). Requirement (c) is the same axis, extended to paid products. FSL restricts by competition ("Competing Use"), which under-covers non-competing paid embedding and would let a CRM vendor bundle the tool as a feature. Sentry says this itself: FSL "is not ideal for companies that depend on other business models, such as charging for on-premise use or library embedding."
4. Enterprise familiarity: Elastic, Kibana, Airbyte (platform and connectors) and Apollo Federation/Router ship under ELv2, so procurement and legal teams have already approved it somewhere. The draft is presented as "ELv2 plus two additions" so counsel can diff it in five minutes.

The closest off-the-shelf alternative is n8n's Sustainable Use License, itself a near-verbatim ELv2 derivative. It already satisfies (a) and (c), but its key term "internal business purposes" is defined only in a FAQ, its redistribution clause is narrower than (a), and it grants no trademark permission for the notices it forces you to keep. Section 3.3 explains what the draft borrows from it.

---

## 2. Licence-by-licence mapping to (a) to (d)

Legend: Yes = requirement met as written; Partial = partly met or met only with extra drafting; No = not met.

| Licence | (a) free internal use, modify, redistribute | (b) logo and attribution cannot be stripped | (c) no paid product / hosted service without permission | (d) short, known, enterprise-safe | Verdict |
|---|---|---|---|---|---|
| Elastic License 2.0 | Yes | Partial (notices clause; Elastic reads it as covering in-product logos, but no explicit UI/logo wording and no trademark permission) | Partial (blocks hosted/managed service only; paid embedding and bundling are expressly allowed) | Yes (about 700 words, 2021, Elastic/Airbyte/Apollo) | Best base |
| FSL-1.1-MIT / Apache-2.0 | Yes | No (copyright notices only; converts to MIT/Apache after 2 years) | Partial (blocks competing commercial products; not non-competing embedding) | Yes (short, plain; Sentry, Codecov, Keygen) | Good second choice if you accept the 2-year conversion |
| Business Source License 1.1 | Partial (default is non-production only; production needs a custom Additional Use Grant) | No (must "conspicuously display this License"; nothing about logos) | Yes via Additional Use Grant (HashiCorp's "hosted or embedded" text is a good model) | Partial (known, but every BUSL is a different licence; converts to a GPL-compatible licence within 4 years) | Workable, heavier |
| PolyForm Noncommercial 1.0.0 | No (a company's sales team is commercial use) | Partial ("Required Notice:" lines must travel with copies) | Over-broad (bans all commercial use, including internal) | Partial (short and clean, but "noncommercial" frightens business users) | Not a fit |
| PolyForm Shield 1.0.0 | Yes | Partial (Required Notice lines only) | Partial (bans competing products, paid or free; allows non-competing paid embedding) | Partial (short, less known) | Not a fit |
| PolyForm Small Business 1.0.0 | No (only companies under 100 people and under USD 1M revenue) | Partial | Implicit (large companies need a commercial licence for anything) | No for enterprise | Not a fit |
| Sustainable Use License 1.0 (n8n) | Yes for internal business use; redistribution only "free of charge for non-commercial purposes" | Partial (same notices clause as ELv2) | Yes ("internal business purposes" only; commercial embedding or hosting needs an agreement) | Yes (ELv2-derived, short; "internal business purposes" undefined in the text) | Closest off-the-shelf |
| Commons Clause v1.0 (addendum) | Yes | No (relies on the base licence) | Partial (blocks selling the software itself, including hosting and consulting fees; expressly allows embedding in a larger paid product) | No (2018 backlash; consulting/support sting; unclear interplay with the base licence) | Not a fit |
| Fair Source definition (fair.io) | n/a (a definition, not a licence) | n/a | n/a | n/a | Only applies if you add delayed open source publication |
| Server Side Public License v1 | Yes, but copyleft: modified copies must ship source under SSPL | Partial (Appropriate Legal Notices: copyright, warranty, licence; section 7 additional terms allow reasonable attribution) | No (does not ban paid products; demands full stack source for SaaS use) | No (copyleft, long, banned by many enterprise policies) | Not a fit |

### 2.1 Elastic License 2.0 (fetched: elastic.co/licensing/elastic-license and the FAQ)

Structure: Acceptance, Copyright License, Limitations, Patents, Notices, No Other Rights, Termination (30-day cure), No Liability, Definitions. Three limitations, quoted:

- "You may not provide the software to third parties as a hosted or managed service, where the service provides users with access to any substantial set of the features or functionality of the software."
- "You may not move, change, disable, or circumvent the license key functionality in the software, and you may not remove or obscure any functionality in the software that is protected by the license key."
- "You may not alter, remove, or obscure any licensing, copyright, or other notices of the licensor in the software. Any use of the licensor's trademarks is subject to applicable law."

Elastic FAQ on the third limitation: "This limitation is intended to protect our software and brand by preventing folks from removing notice of the license, copyrights, or trademarks, such as the terms Elasticsearch and Kibana, in-product logos, etc."

Elastic FAQ on embedding: "You may freely use Elasticsearch inside your SaaS or self-managed application, and redistribute it with your application, provided you follow the three limitations." So paid embedding is allowed under ELv2 as written, which is why (c) needs an extra limitation. Contractors setting up the software for clients' internal use are explicitly fine.

Reuse: Elastic's launch post (Feb 2021) says "We created ELv2 to hopefully allow others to adopt it" and that it was drafted with Heather Meeker. n8n's Sustainable Use License is a near-verbatim derivative, so deriving from the text has precedent. Do not call a modified version "Elastic License"; give it its own name.

### 2.2 Functional Source License 1.1 (fetched: FSL-1.1-MIT template; Sentry's LICENSE.md for the Apache-2.0 variant)

Grant covers use, copy, modify, derivative works, public performance/display, redistribution "for any Permitted Purpose". A Permitted Purpose is anything except a Competing Use: "making the Software available to others in a commercial product or service that (1) substitutes for the Software; (2) substitutes for any other product or service we offer using the Software that exists as of the date we make the Software available; or (3) offers the same or substantially similar functionality as the Software." Internal use, non-commercial education and research, and professional services are named as permitted.

Redistribution: include the terms and "not remove any copyright notices". Trademarks: "Except for displaying the License Details and identifying us as the origin of the Software, you have no right ... to use our trademarks." Grant of Future License: irrevocable MIT (or Apache-2.0) licence effective on the second anniversary of each version's release.

Fit: (a) yes. (b) weak: only copyright notices, and after two years MIT applies to that version. (c) partial: catches a paid substitute or "substantially similar" product, not a non-competing paid product that embeds the tool. (d) strong: plain English, one page, growing adoption (Sentry, Codecov, GitButler, PowerSync, Keygen's FCL variant). The only reason not to pick it is that its defining feature, the two-year conversion, dissolves (b) and (c) per version.

### 2.3 Business Source License 1.1 (fetched: mariadb.com/bsl11 and HashiCorp's Terraform LICENSE as a filled-in example)

Parameterised: Licensor, Licensed Work, Additional Use Grant, Change Date, Change License. Default grant is "copy, modify, create derivative works, redistribute, and make non-production use". Production use exists only if the Additional Use Grant allows it. Change Date is at most four years; the Covenants of Licensor require a GPLv2-compatible Change License. "You must conspicuously display this License on each original or modified copy." "This License does not grant you any right in any trademark or logo of Licensor ... (provided that you may use a trademark or logo of Licensor as expressly required by this License)."

HashiCorp's Additional Use Grant is a useful model for (c): production use is allowed "provided Your use does not include offering the Licensed Work to third parties on a hosted or embedded basis in order to compete", with "Embedded" defined as "including the source code or executable code from the Licensed Work in a competitive offering" or packaging so that the Licensed Work "must be accessed or downloaded for the competitive offering to operate", and "Hosting or using the Licensed Work(s) for internal purposes within an organization is not considered a competitive offering."

Fit: (a) only with a custom grant. (b) no logo term. (c) yes with drafting. (d) mixed: enterprise counsel know BUSL (MariaDB, Terraform, Couchbase, Sentry until 2023), but Sentry's stated reason for leaving it applies here: "every BSL is a different license", so compliance teams "can't adopt a blanket rule". Also expires within four years.

### 2.4 PolyForm Noncommercial 1.0.0 (fetched)

"Any noncommercial purpose is a permitted purpose." Personal uses and named noncommercial organisations (charities, educational institutions, public research, public safety or health, environmental, government) are covered. Notices: pass on the terms and any "Required Notice:" lines. 32-day cure. Fails (a) outright: a company using it for its sales team is commercial use.

### 2.5 PolyForm Shield 1.0.0 (fetched)

"Any purpose is a permitted purpose, except for providing any product that competes with the software or any product the licensor or any of its affiliates provides using the software." Competition is defined broadly: different interfaces, platforms and languages still compete, and "Goods and services compete even when provided free of charge." Includes New Products, Discontinued Products (with an optional "Licensor Line of Business:" line) and Sales of Business clauses. Fit: (a) yes; (b) Required Notice lines only; (c) wrong axis (competition, not payment), and it blocks free competing forks that (a) wants to allow; (d) short but rarely seen by enterprise legal.

### 2.6 PolyForm Small Business 1.0.0 (fetched)

Permitted only if "your company has fewer than 100 total individuals working as employees and independent contractors, and less than 1,000,000 USD (2019) total revenue in the prior tax year", CPI-adjusted. Exactly the wrong shape for enterprise sales teams.

### 2.7 Sustainable Use License 1.0, n8n (fetched: n8n LICENSE.md and the docs FAQ)

Same skeleton and wording as ELv2 with the limitations replaced by: "You may use or modify the software only for your own internal business purposes or for non-commercial or personal use. You may distribute the software or provide it to others only if you do so free of charge for non-commercial purposes. You may not alter, remove, or obscure any licensing, copyright, or other notices of the licensor in the software. Any use of the licensor's trademarks is subject to applicable law."

The FAQ does the real work: "all use is allowed unless you are selling a product, service, or module in which the value derives entirely or substantially from n8n functionality." Not allowed: "White-labeling n8n and offering it to your customers for money", "Hosting n8n and charging people money to access it". Allowed: internal data sync, building nodes and integrations, consulting, setup and maintenance. Commercial embedding requires "a separate commercial agreement" (n8n Embed). n8n moved to this from Apache-2.0 plus Commons Clause specifically to lift the ban on paid consulting and support.

Fit: (a) yes for internal use, but "distribute ... only ... free of charge for non-commercial purposes" is narrower than (a) (a consultancy handing a free copy to a client is arguably commercial). (b) same as ELv2. (c) yes, the closest existing match. (d) short, but the undefined "internal business purposes" generates recurring confusion (the n8n community threads from August 2026 about backend use and tenant credentials show how much interpretation the FAQ has to carry). Also no trademark permission for the notices it makes you keep.

### 2.8 Commons Clause v1.0 (fetched: commonsclause.com)

An addendum bolted onto an OSS licence: "the License does not grant to you, the right to Sell the Software", where Sell means providing "for a fee or other consideration (including without limitation fees for hosting or consulting/support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software." The FAQ is explicit that you "may embed and redistribute Commons Clause software in a larger product, and you may distribute and even 'sell' ... your product", which is the opposite of (c). The consulting/support sting is what pushed n8n off it, and Redis abandoned it in 2019. Its FAQ also states plainly it is not open source.

### 2.9 Fair Source definition (fetched: fair.io, fair.io/about, fair.io/licenses)

Fair Source Software "is publicly available to read", "allows use, modification, and redistribution with minimal restrictions to protect the producer's business model", and "undergoes delayed Open Source publication (DOSP)". DOSP is "a key differentiator of Fair Source from Open Core and other approaches." Recommended licences: FSL (flagship), Fair Core License (FSL plus ELv2-style licence-key protection, drafted by Heather Meeker for Keygen), and BUSL. A licence that keeps (b) and (c) permanently is not Fair Source, so do not use the badge unless you add a conversion date.

### 2.10 Server Side Public License v1 (fetched: mongodb.com)

GPLv3 text plus section 13: "If you make the functionality of the Program or a modified version available to third parties as a service, you must make the Service Source Code available via network download to everyone at no charge", where Service Source Code covers "management software, user interfaces, application program interfaces, automation software, monitoring software, backup software, storage software and hosting software". Section 5(d) requires interactive interfaces to display Appropriate Legal Notices (copyright notice, no-warranty statement, licence pointer). Section 7 permits added terms "requiring preservation of specified reasonable legal notices or author attributions" and declining trademark rights. It never bans paid products; it demands source. Fails (c) and (d).

---

## 3. How projects protect logos and branding

### 3.1 Trademark clauses in the standard licences

- **Apache-2.0**: section 4(c) requires derivative works to "retain ... all copyright, patent, trademark, and attribution notices from the Source form of the Work"; 4(d) carries the NOTICE file forward; section 6 grants no trademark permission "except as required for reasonable and customary use in describing the origin of the Work". Only source-form notices are protected; UI logos can be removed.
- **MPL 2.0**: section 2.3 "does not grant any rights in the trademarks, service marks, or logos of any Contributor (except as may be necessary to comply with the notice requirements in Section 3.4)"; 3.4 forbids removing or altering licence notices in Source Code Form "except ... to remedy known factual inaccuracies". The parenthetical in 2.3 is the model for the narrow trademark permission the draft needs.
- **MongoDB**: SSPL section 7(e) declines trademark rights; a separate Trademark Usage Guidelines page allows use "only to identify and distinguish MongoDB products and services", forbids use in product, company or domain names, and says "you also may not edit, change, distort, recolor, or reconfigure our marks (including our leaf logo)". Brand control lives in policy, not in the licence.
- **AGPLv3 section 7**: additional terms may (b) require "preservation of specified reasonable legal notices or author attributions in that material or in the Appropriate Legal Notices displayed by works containing it", (c) prohibit "misrepresentation of the origin of that material" or require modified versions to "be marked in reasonable ways as different from the original version", and (e) decline trademark rights. Appropriate Legal Notices means a copyright notice, warranty statement and licence pointer, not a logo. SugarCRM's 2007-2009 "logo on every screen via section 7" terms were widely criticised as exceeding what 7(b)'s "reasonable" allows (Rick Moen, OSI license-review, 2016).

### 3.2 Attribution-preservation licences ("badgeware")

- **Attribution Assurance License** (OSI-approved, 2002, BSD-derived): binary redistribution requires, "each time the resulting executable program or a program dependent thereon is launched, a prominent display (e.g., splash screen or banner text) of the Author's attribution information": name, professional identification, URL. Clause 3 withholds endorsement rights. The author placed the template in the public domain; it is obscure and effectively unused.
- **Common Public Attribution License 1.0** (OSI-approved July 2007; used by Socialtext, Mule, OpenProj, early Reddit): section 14 lets the Original Developer require, each time the software "is launched or initially run", a prominent GUI display of Attribution Information limited to "(a) a copyright notice including the name of the Original Developer; (b) a word or one phrase (not exceeding 10 words); (c) one graphic image provided by the Original Developer; and (d) a URL". No GUI, no duty. 14(d): trademarks in the Attribution Information "may only be used with the permission of their owners, or under circumstances otherwise permitted by law or as expressly set out in this License."
- **History**: SugarCRM's SPL 1.1.3 (MPL 1.1 plus "Exhibit B") required a 106x23 "Powered by SugarCRM" logo on every UI screen of every derivative; about two dozen Web 2.0 firms cloned it (Zimbra, Alfresco, Socialtext). Critics argued it breached Open Source Definition clauses 3, 6 and 10. CPAL was the negotiated minimum and was approved; most adopters then moved to GPLv3/AGPLv3 with section 7 badges, and CPAL saw little use. LWN's 2007 lesson is the important one for drafting: a licence that compels display of a logo while granting no trademark rights puts the licensee in a trap; a court would probably imply the trademark licence, but write it explicitly.

### 3.3 Company approaches

- **Plausible Analytics** (AGPLv3 plus trademark policy, fetched plausible.io/trademark): the licence "does not include a license to use our trademarks". Commercial hosting, resale, bundled or modified versions need written permission and, if granted, "You must remove all logos and use your own branding". In 2024 they renamed the self-hosted build Plausible Community Edition with a different logo and registered trademarks in the US and EU. Their lever is de-branding forks, the mirror image of (b).
- **Twenty CRM** (AGPLv3 plus section 7 application exception, fetched LICENSE and .github/TRADEMARK.md): forks distributed or operated publicly must "give it its own name and branding"; "powered by Twenty" statements are allowed; using the Twenty logo as your own is not. Again trademark is used to restrict use of the marks, not to force retention.
- **Cal.com**: until April 2026 the core was AGPLv3 with a commercial /ee folder ("may only be used in production, if you ... have a valid Cal.com Enterprise Edition subscription"). "Powered by Cal.com" branding was removable only via a paid-plan toggle ("disable Cal.com branding"), a product gate rather than a licence clause. On 2026-04-15 Cal.com moved the commercial codebase private and relaunched the public repo as Cal.diy under MIT ("It was 'source-available' before, which is now 'closed source'"). Two lessons: branding retention was enforced by feature gating, and the company eventually decided the source-available middle ground was not worth it for the commercial edition.
- **Sentry** (fetched open.sentry.io/licensing): FSL-1.1-Apache-2.0 for the Sentry and Codecov web apps, Apache-2.0 by default, MIT for SDKs. Brand protection rests on the FSL Trademarks clause; no public trademark policy page surfaced. Sentry's 2023 post admits trademarks alone were not enough under BSD-3: "While we had registered trademarks, the license granted them enough rights over the software."
- **Elastic and n8n**: keep the "may not alter, remove, or obscure any ... notices" limitation inside the copyright licence and treat in-product logos as notices. This is the pattern the draft follows, made explicit.

### 3.4 Is a "may not remove the logo" clause enforceable, and under which law?

**Copyright (yes, if drafted as a condition with a nexus to an exclusive right).**
- *Jacobsen v. Katzer*, 535 F.3d 1373 (Fed. Cir. 2008): Artistic License terms requiring retention of copyright notices and marking of changes are conditions, so exceeding them is copyright infringement with injunctive relief available. The court quoted Nimmer section 10.15: a condition "that a licensee must affix a proper copyright notice to all copies ... will render a publication devoid of such notice without authority from the licensor and therefore, an infringing act", and held that "attribution and modification transparency requirements directly serve ... a significant economic goal of the copyright holder that the law will enforce."
- *MDY Industries v. Blizzard*, 629 F.3d 928 (9th Cir. 2010): for breach of a licence term to be infringement rather than mere contract breach, "there must be a nexus between the condition and the licensor's exclusive rights of copyright" (reproduction, distribution, derivative works). Removing or hiding the logo means modifying the software (a derivative work) and distributing or displaying the modified copy, so the nexus exists. Draft the clause as "you may not modify the software to remove ... and modified copies must retain ...", and phrase the whole licence grant as "subject to the limitations" (ELv2 already does), rather than as a free-floating duty to show a badge at runtime.
- *Doe v. GitHub* (N.D. Cal. 2024): attribution and notice terms in MIT, BSD, Apache and GPL licences are likely conditions, and a licensor may also sue in contract for their breach. Either route is open.

**DMCA section 1202 (a second copyright lever, with limits).** Removing "copyright management information" (the name of the author or owner, the title, the terms and conditions of use, 17 U.S.C. 1202(c)) and distributing copies knowing it was removed is actionable, with statutory damages of USD 2,500 to 25,000 per violation (1203(c)(3)(B)). *Mango v. BuzzFeed*, 970 F.3d 167 (2d Cir. 2020) confirmed the double-scienter standard and that CMI need not be affixed by the owner personally. Limits: Ninth Circuit district courts require the copy to be identical (*Doe v. GitHub*, 2024, dismissing the 1202(b) claim with prejudice for lack of identicality), so a heavily modified fork may escape 1202; and a bare logo image is not obviously CMI. Practical fix: put the owner's name, the copyright line and a licence pointer next to the logo so the badge itself is CMI.

**Trademark (no, for compelling display; yes, for stopping misuse).** *Dastar v. Twentieth Century Fox*, 539 U.S. 23 (2003): the Lanham Act's "origin of goods" means the producer of the tangible product, not the author of the creative content, so there is no trademark-law right of attribution for uncredited copying. Trademark law cannot force anyone to keep your logo. It does the reverse: it stops people using your name or logo confusingly (the MongoDB, Plausible and Twenty policies). Consequences for drafting: (1) the keep-the-logo duty must be a copyright/contract condition; (2) the licence must grant a narrow trademark permission to display the marks as placed, otherwise "must display" and "no trademark rights" contradict each other (the CPAL trap); (3) add a separate "no endorsement, mark modified versions" clause so trademark law is available against confusing forks; (4) register the marks (Plausible did, in the US and EU), because an unregistered mark is much harder to enforce outside the US.

**Contract (the route outside the US).** In the UK and EU, licence terms are enforced as contract, and ELv2-style automatic termination turns continued use after breach into infringement. Do not rely on moral rights: UK CDPA s.79(2)(a) excludes computer programs from the right to be identified as author; countries that do extend it (Germany's UrhG s.13) give it to the human author, not the company, and it cannot be assigned. Berne 6bis is not self-executing.

**Keep it reasonable.** Courts and communities have both pushed back on heavy badgeware. Copy CPAL's limits (one logo, one short phrase, one URL, only where a UI exists), make the requirement technology-neutral (no UI, no display duty), keep ELv2's 30-day cure period, and do not require branding on user-generated output. That keeps the clause enforceable and keeps (d).

---

## 4. Draft licence

Working name: **[PROJECT] Source-Available License 1.0** ("[PROJECT]-SAL-1.0"). Fill in the bracketed terms. It is ELv2 with (i) a Permitted Use section for enterprise clarity, (ii) two extra limitations (Commercial Offering; Attribution Marks), (iii) a narrow trademark permission, (iv) a Commercial License paragraph, and (v) definitions for the new terms. Everything else is ELv2 verbatim or near-verbatim.

```text
[PROJECT] Source-Available License
Version 1.0, [DATE]. Based on the Elastic License 2.0, with additional terms on commercial use and attribution.

Acceptance
By using the software, you agree to all of the terms and conditions below.

Copyright License
The licensor grants you a non-exclusive, royalty-free, worldwide, non-sublicensable, non-transferable license to use, copy, distribute, make available, and prepare derivative works of the software, in each case subject to the limitations and conditions below.

Permitted Use
For clarity, and subject to the limitations below, you may:
1. use the software for your company's own internal purposes, including in production and by your company's sales, marketing and other customer-facing teams;
2. let contractors, agencies and service providers use the software on your company's behalf;
3. modify the software and keep your modifications private, or share them free of charge under these terms;
4. distribute copies of the software, modified or unmodified, to anyone free of charge under these terms;
5. provide paid professional services (installation, configuration, customization, training, support) to a customer who uses the software under these terms on infrastructure that customer controls; and
6. use, share and sell any Output for any purpose. Output is not subject to these terms.

Limitations
1. You may not sell the software, and you may not include, embed, bundle, integrate or otherwise make the software, or any substantial set of its features or functionality, available to third parties as part of, or in connection with, a Commercial Offering.
2. You may not provide the software to third parties as a hosted or managed service, where the service provides users with access to any substantial set of the features or functionality of the software.
3. You may not remove, hide, obscure, alter, resize below legibility, or replace any Attribution Mark, or any licensing, copyright or other notice of the licensor, wherever it appears in the software, including in user interfaces, documentation and source files. If you distribute a modified version, it must retain the Attribution Marks and must display a prominent notice that it has been modified and is not provided or endorsed by the licensor. A form of the software that has no user interface need only retain the notices in its source files and documentation.
[4. You may not move, change, disable, or circumvent the license key functionality in the software, and you may not remove or obscure any functionality in the software that is protected by the license key.] (delete if the software has no license-key-gated features)
Limitations 1 and 2 do not apply to your company's internal use of the software, and do not apply to the extent you hold a Commercial License that permits the activity.

Trademarks
Solely to comply with Limitation 3, the licensor grants you a limited, non-exclusive, non-transferable, royalty-free license to reproduce and display the Attribution Marks, unmodified and in the position and form in which the software displays them. You may also use the licensor's name to truthfully describe the origin of the software (for example, "built on [PROJECT]"). These terms grant no other trademark rights. You may not use the licensor's trademarks as part of your own product, service, company or domain name, or in any way that suggests the licensor endorses, sponsors or is affiliated with you or your modified version.

Patents
The licensor grants you a license, under any patent claims the licensor can license, or becomes able to license, to make, have made, use, sell, offer for sale, import and have imported the software, in each case subject to the limitations and conditions in this license. This license does not cover any patent claims that you cause to be infringed by modifications or additions to the software. If you or your company make any written claim that the software infringes or contributes to infringement of any patent, your patent license for the software granted under these terms ends immediately. If your company makes such a claim, your patent license ends immediately for work on behalf of your company.

Notices
You must ensure that anyone who gets a copy of any part of the software from you also gets a copy of these terms.
If you modify the software, you must include in any modified copies of the software prominent notices stating that you have modified the software.

Commercial License
If you want to do anything these terms do not allow, including embedding the software in a paid product, offering it as a hosted or managed service, or distributing it without the Attribution Marks (white-labeling), you need a separate written Commercial License from the licensor. Commercial Licenses are available on request at [EMAIL / URL]. Nothing in these terms prevents the licensor from offering the software under other terms.

No Other Rights
These terms do not imply any licenses other than those expressly granted in these terms.

Termination
If you use the software in violation of these terms, such use is not licensed, and your licenses will automatically terminate. If the licensor provides you with a notice of your violation, and you cease all violation of this license no later than 30 days after you receive that notice, your licenses will be reinstated retroactively. However, if you violate these terms after such reinstatement, any additional violation of these terms will cause your licenses to terminate automatically and permanently.

No Liability
As far as the law allows, the software comes as is, without any warranty or condition, and the licensor will not be liable to you for any damages arising out of these terms or the use or nature of the software, under any kind of legal claim.

Definitions
The "licensor" is [LEGAL ENTITY], the entity offering these terms, and the "software" is the software the licensor makes available under these terms, including any portion of it.
"You" refers to the individual or entity agreeing to these terms.
"Your company" is any legal entity, sole proprietorship, or other kind of organization that you work for, plus all organizations that have control over, are under the control of, or are under common control with that organization. "Control" means ownership of substantially all the assets of an entity, or the power to direct its management and policies by vote, contract, or otherwise. Control can be direct or indirect.
"Third party" means anyone other than you and your company, and excludes contractors, agencies and service providers while acting on your company's behalf.
"Commercial Offering" means any product or service that you or your company provide to third parties for payment or other consideration, including subscriptions, license fees, usage fees, revenue share, or pricing bundled with other goods or services.
"Commercial License" means a separate written license agreement between you and the licensor that expressly permits activity otherwise prohibited by these terms.
"Attribution Marks" means the [PROJECT] name, the [PROJECT] logo, the "Powered by [PROJECT]" notice and link, and the copyright and license notices, in each case as they appear in the software as distributed by the licensor.
"Output" means documents, data, content or other material you create using the software, other than the software itself or any substantial portion of it.
"Your licenses" are all the licenses granted to you for the software under these terms.
"Use" means anything you do with the software requiring one of your licenses.
"Trademark" means trademarks, service marks, and similar rights.
```

### 4.1 How the draft satisfies (a) to (d)

- (a): Copyright License plus Permitted Use items 1 to 4. Internal production use by sales teams, contractor use, private modification and free redistribution are all named. Output is carved out entirely so a sales team can send what it makes to customers without a licence question.
- (b): Limitation 3 (drafted as a restriction on modification and distribution to keep the *MDY* nexus), the "modified, not endorsed" marking (AGPL 7(c) idea), the "no UI, no duty" sentence (CPAL idea), and the Trademarks section which grants the narrow display permission (MPL 2.3 idea) while withholding everything else so trademark law remains available against confusing forks.
- (c): Limitation 1 (paid products, bundling, integration) and Limitation 2 (hosted or managed service, ELv2 verbatim). "Commercial Offering" is defined by consideration, not by competition, so a non-competing paid product is still caught. Professional services on a customer's own instance are expressly allowed (FSL and n8n approach) to avoid the Commons Clause consulting problem.
- (d): 85 lines, ELv2 skeleton so counsel can diff it, no copyleft, no source-disclosure duties, no "non-commercial" ambiguity, explicit "internal use is fine" sentence, 30-day cure, and a single pointer for the commercial route.

### 4.2 Decisions to make before shipping

1. **Free hosted instances.** Limitation 2 (ELv2 verbatim) bans hosted or managed services to third parties whether paid or free. Requirement (c) says "paid/hosted", which can be read either way. Keeping the ELv2 wording is safer (a "free" hosted instance monetised by ads or lead capture would otherwise slip through). If you want to allow genuinely free public instances, add "for payment or other consideration" to Limitation 2.
2. **Branding on Output.** The draft deliberately does not require a "Made with [PROJECT]" mark on generated documents; sales teams will not accept it and it would undermine (d). If you want it, add it as a separate, clearly limited sentence.
3. **Licence-key clause.** Keep Limitation 4 only if a commercial edition gates features by key.
4. **Delayed open source publication.** If community goodwill matters more than permanent brand protection, add an FSL-style "Grant of Future License" (Apache-2.0 after two years per version). That earns the Fair Source label but ends (b) and (c) for each version after two years. Not recommended given the stated requirements.
5. **Name.** Do not call it "Elastic License"; use "[PROJECT] Source-Available License 1.0" and an SPDX LicenseRef id such as `LicenseRef-[PROJECT]-SAL-1.0`.

---

## 5. README licence summary (10 lines)

| What you want to do | Free under [PROJECT]-SAL-1.0 | Commercial licence |
|---|---|---|
| Download, install and run it in production for your own company, including your sales team | Yes | Yes |
| Modify the code and keep your changes private | Yes | Yes |
| Share copies or your fork with anyone, free of charge | Yes, keep the licence and the [PROJECT] branding | Yes |
| Have contractors or agencies run it on your company's behalf | Yes | Yes |
| Share or sell what you create with it (decks, documents, data) | Yes, output is yours | Yes |
| Paid consulting, setup, training or support on a customer's own instance | Yes | Yes |
| Bundle or embed it in a product or service you charge for | No | Yes |
| Offer it to others as a hosted or managed service | No | Yes |
| Remove or hide the [PROJECT] logo, name, "Powered by" notice or copyright notices (white-label) | No | Yes, on request |
| Use the [PROJECT] name or logo as your own brand, or imply we endorse your version | No | Separate trademark licence |

---

## 6. README wording

Use "source-available", never "open source". Every project that blurred the line (Sentry and Codecov under BUSL in 2023, Commons Clause adopters in 2018) had to retract. Suggested block:

> ## License
> [PROJECT] is **source-available**: the code is public and free to use, modify and share, including in production inside companies and by their sales teams, under the [PROJECT] Source-Available License 1.0 (based on the Elastic License 2.0). It is not open source under the OSI definition: you cannot sell it, embed it in a paid product, offer it as a hosted service, or remove the [PROJECT] branding without a commercial licence. See [LICENSE.md](LICENSE.md) and the [licence FAQ](LICENSE-FAQ.md). Commercial licences: [email].

One-line tagline for the repo description or badge: `Source-available · free for internal use · commercial licence for embedding and hosting`.

Notes on labels:
- **"Free for internal use"** is accurate and is the phrase enterprise buyers understand; lead with it.
- **"Open core"** implies an OSI-licensed core plus proprietary extras (GitLab, PostHog). This project's core is source-available, so "open core" is not accurate; say "source-available core, commercial licence for embedding, hosting and white-label" instead. If you later split out a paid edition, the honest label is "source-available core" not "open core".
- **"Fair-code"** (n8n's term, faircode.io) fits ELv2-style licences and is a reasonable secondary label. **"Fair Source"** (fair.io) requires a delayed open source conversion; do not use it without one.
- Ship a `LICENSE-FAQ.md` with worked examples in the Elastic and n8n style (cat-picture SaaS, contractor for a client, MSP). The FAQ, more than the licence text, is what removes friction for enterprise legal.
- GitHub will show "View license" rather than a recognised licence name; that is expected for custom licences. Set `"license": "SEE LICENSE IN LICENSE.md"` in package.json (or the equivalent) and use `LicenseRef-[PROJECT]-SAL-1.0` in SBOMs.

---

## 7. Flags for legal review

1. **Text reuse.** The draft derives from ELv2. Elastic invited adoption and n8n derived from it, but the ELv2 text carries no explicit licence of its own. Have counsel confirm the derivation and the new name are acceptable.
2. **Choice of law and forum.** ELv2 has none. Decide whether to add one (licensor's jurisdiction) or leave it silent as ELv2 does.
3. **Trademark registration.** Register the name and logo (word mark and figurative mark) in your key markets, as Plausible did. Limitation 3 and the Trademarks section are only as strong as the marks behind them.
4. **CMI placement.** Put the legal name, copyright line and licence pointer adjacent to the logo in the UI and source headers so the branding qualifies as copyright management information under 17 U.S.C. 1202.
5. **Contributor agreement.** To sell commercial licences that cover community contributions, you need a CLA (or a DCO with an explicit outbound relicensing grant). Without it, contributions come back to you only under [PROJECT]-SAL-1.0 and cannot be relicensed commercially. Airbyte's 2025 ELv2 post shows the same issue handled by moving contributions under ELv2 going forward.
6. **Dependencies.** A source-available work cannot be distributed together with GPL or AGPL code as one program. Audit dependencies for copyleft licences; MIT, BSD and Apache-2.0 are fine.
7. **Consumer and unfair-terms law.** Individual users in the EU and UK may benefit from consumer protection that limits the No Liability clause; ELv2's "as far as the law allows" already hedges this.
8. **Condition drafting.** Keep "subject to the limitations and conditions below" in the grant and keep Limitation 3 phrased as a restriction on modifying and distributing, to preserve the *Jacobsen* / *MDY* copyright route rather than contract-only remedies.
9. **Related case to check.** *Neo4j v. PureThink* (N.D. Cal. 2021, aff'd 9th Cir. 2022, unpublished) concerned a licensee stripping an added restriction from an AGPL-based licence and calling the result open source; it is often cited on the enforceability of licensor-added restrictions and on false "open source" claims. Not fetched in this session; verify before relying on it.

---

## 8. Sources fetched on 2026-09-07

Licence texts: elastic.co/licensing/elastic-license and /faq; fsl.software and the FSL-1.1-MIT template (getsentry/fsl.software); getsentry/sentry LICENSE.md (FSL-1.1-Apache-2.0); mariadb.com/bsl11; hashicorp/terraform LICENSE (BUSL 1.1 with parameters); polyformproject.org licences noncommercial, shield and small-business 1.0.0; n8n-io/n8n LICENSE.md and docs.n8n.io/privacy-and-security/sustainable-use-license; commonsclause.com; fair.io, fair.io/about, fair.io/licenses; fcl.dev; mongodb.com/legal/licensing/server-side-public-license; apache.org/licenses/LICENSE-2.0; mozilla.org/MPL/2.0; gnu.org/licenses/agpl-3.0; opensource.org/license/attribution-php; opensource.org/license/cpal_1.0.

Branding: plausible.io/trademark and plausible.io/blog/community-edition; twentyhq/twenty LICENSE and .github/TRADEMARK.md; calcom/cal.com README and packages/features/ee/LICENSE, calcom/cal.diy LICENSE, cal.com/blog/cal-diy-open-source-to-closed-source and cal.com/blog/calcom-v6-4; open.sentry.io/licensing, blog.sentry.io FSL and BUSL posts; mongodb.com/legal/trademark-usage-guidelines; elastic.co/blog/elastic-license-v2; airbyte.com/blog/move-to-elv2; apollographql.com/trust/licensing; LWN "Open-source badgeware" (2007), The Register on CPAL approval, OSI license-review badgeware history (2016), OSS Watch CPAL overview, Linux Gazette 148.

Enforceability: Jacobsen v. Katzer (Fed. Cir. 2008) opinion and Google's Open Source Casebook remedies chapter; MDY v. Blizzard (9th Cir. 2010) opinion; Dastar v. Twentieth Century Fox (2003, LII); Mango v. BuzzFeed (2d Cir. 2020); Doe v. GitHub orders (N.D. Cal. 2024) on section 1202(b) identicality and licence conditions; UK CDPA 1988 ss.77 and 79; EU Directive 2009/24/EC.

Not retrievable this session: fsl.software raw FSL-1.1-Apache-2.0 template (used Sentry's LICENSE.md instead); sentry.io/trademark (no policy page).
