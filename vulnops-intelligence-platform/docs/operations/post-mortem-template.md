# Post-incident review (blameless) — template

**Incident ID:** INC-____  
**Date (UTC):** YYYY-MM-DD  
**Severity:** SEV-__  
**Facilitator:** __________________  
**Participants:** __________________  

---

## Summary

One paragraph: what broke, who was impacted, how long.

## Customer / user impact

- Duration of degraded service:  
- Affected regions / tenants:  
- Data impact (none / corruption / exposure):  

## Timeline (UTC)

| Time | Event |
|------|--------|
| HH:MM | Detection (alert / customer / internal) |
| HH:MM | Mitigation start |
| HH:MM | Service restored |
| HH:MM | Post-incident tasks opened |

## Root cause

Technical cause (not individual blame). Include contributing factors (deploy, config, dependency, capacity, process).

## What went well

-  

## What went poorly

-  

## Action items

| ID | Action | Owner | Due |
|----|--------|-------|-----|
| 1 | | | |

Link tickets in your tracker.

## Lessons

- **Detection:** Was time-to-detect acceptable vs SLO?  
- **Mitigation:** Runbooks ([ETL](../runbooks/etl-failure.md), [PBI](../runbooks/pbi-refresh-failure.md)) accurate?  
- **Communication:** Stakeholder updates timely?  

## Error budget

Approximate **availability** or **latency** budget consumed this incident (tie to [SLOs](slos-and-alerting.md)).

---

*Blameless principle: we improve systems and processes, not assign fault to individuals.*
