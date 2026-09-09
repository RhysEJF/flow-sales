# Teams: one FlowSales, many machines, no hub

HubSpot and Granola stay the record. Every machine keeps its own `.flow-sales` store and pulls for itself. The only thing a team shares is the judged assessments, because those cost money to produce, and they travel through a folder the team already syncs. Nobody runs a server, nobody has to be the hub, nobody needs a GitHub account, and the first person to install can be a rep or the ops person.

## The three rules

1. **Each machine pulls its own data.** A rep's daily sync pulls their own deals since the last pull (`--owner me` on the private-app route, an owner filter on the connector route), a few dozen deals, seconds. The ops person or a manager pulls the whole pipeline the same way for the team report. Freshness never depends on a colleague.
2. **Nobody needs a token.** The HubSpot connector the plugin ships signs each person in as themselves, and they see what HubSpot lets them see. The private-app token is the route for an unattended machine or an ops person who prefers it; a rep never handles it.
3. **Judged deals are shared through a folder.** Before judging a deal, the planner looks in the team folder for an assessment with the same deal id, the same input hash (exactly these interactions) and the same rubric hash. If it is there it is reused. After judging, new assessments are copied out. A stale or missing folder never changes a number; it only costs a repeat judging.

## Why it exists, in the words setup uses

Every deal FlowSales scores produces one judged file, and producing it costs model tokens. Teammates who run FlowSales on the same deals would each pay to produce the same file again, unless the files sit in a folder the team already syncs. The folder holds those judged files only, never the calls or emails. Skipping it is safe: everything works alone.

How a later rep finds it: their own sync client. When the folder was created inside a shared Drive or OneDrive folder the rep also syncs, it is on their disk and setup offers it. Otherwise the team person tells them the path. A cloud session sees nothing on the Mac, so the question is not asked there.

## The folder

```
<any folder the team syncs>/FlowSales/
  README.txt          what this is, who should see it
  team.json           created when, by whom
  assessments/
    hs_1001.json      one judged assessment per deal, the same shape as the local one
```

Create it with `fs.py team init <path>` (setup asks). Join it with `fs.py team join <path>`, or let setup find it: `fs.py team candidates` looks for a folder named FlowSales with an `assessments/` inside, up to four folders deep, under the working folder (where a folder added to a Cowork session appears) and under `~/Library/CloudStorage/*`, `~/Google Drive*`, `~/My Drive`, `~/Dropbox*`, `~/OneDrive*`, `~/Box*` and `~/Nextcloud`. `fs.py team status` compares the folder with this store; `fs.py team sync` copies matching assessments in and new ones out (`--pull-only`, `--push-only`); `fs.py team leave` forgets the folder without touching it. Audit and daily-sync run the sync around their judging step on their own.

Privacy: the folder holds scores and quotes for every deal, so it is exactly as private as the folder. Share it with the sales team only. Anything that leaves the sales team goes through the report's names-hidden and one-rep exports.

## What happens when

| Case | What happens |
|---|---|
| Folder out of date | Nothing stale reaches a briefing. Deals and calls come from each machine's own pull. |
| Two people judge the same deal in the same minute | Same inputs, same rubric, two valid files; last writer wins and the content is equivalent. Cost: one duplicate judging. A lease file can remove even that later. |
| Rubric changes | The rubric hash is part of the match; old assessments are ignored and re-judged wherever they are. |
| Folder deleted | Every machine keeps its own copy; the next run repopulates the folder. |
| No folder access | Everything works; deals a teammate also owns are judged twice. |
| Rep leaves | Their assessments stay in the folder; their local store goes with the laptop. |

## What it costs, one Tuesday morning, 200-deal pipeline

Tom pulls 14 deals (3 new calls), reuses 13 judged deals, judges 1. Amira pulls 11, reuses 10, judges 1. Sofia, the manager, pulls the pipeline since Friday (212 deals, 60 new interactions), reuses 209 including Tom's and Amira's from that morning, judges 3. Three small pulls instead of three full ones; five deals judged instead of 237. Without the folder every line still runs and Sofia judges 41 interactions instead of 3.

## Still to build

A lease file in the work folder for the same-minute case, and a per-interaction link record so link resolutions can be shared too. Neither blocks a pilot.
