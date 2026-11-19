import argparse, asyncio, json, hashlib
from pathlib import Path
from .data import read_csv
from .pipeline import pipeline
from .decision import decide
from .agents import autogen_review

_CACHE={}
def run_case(case_id):
    packet=pipeline.invoke(case_id)
    report=decide(packet)
    # Stable idempotency key: repeated case IDs return the same deterministic recommendation.
    key=hashlib.sha256(case_id.encode()).hexdigest()
    if key in _CACHE: return _CACHE[key]
    _CACHE[key]=report
    return report

async def process(case_id):
    report=run_case(case_id)
    review=await autogen_review(report)
    return {'report':report.model_dump(mode='json'),'agent_review':{k:v for k,v in review.items() if k!='report'}}

async def main():
    parser=argparse.ArgumentParser(description='Retail Order Exception & Refund Eligibility Review')
    group=parser.add_mutually_exclusive_group(required=True); group.add_argument('--case',help='Case ID, e.g. C001'); group.add_argument('--all',action='store_true',help='Process all supplied cases')
    parser.add_argument('--json-out',default='reports/latest.json'); parser.add_argument('--no-agents',action='store_true')
    args=parser.parse_args()
    ids=[args.case] if args.case else [r['case_id'] for r in read_csv('cases.csv')]
    results=[]
    for cid in ids:
        try:
            report=run_case(cid)
            review={'mode':'not_run','transcript':[]} if args.no_agents else await autogen_review(report)
            results.append({'report':report.model_dump(mode='json'),'agent_review':{k:v for k,v in review.items() if k!='report'}})
            print(f"{cid}: {report.recommendation.value} | {report.explanation}")
        except (KeyError,ValueError) as exc:
            results.append({'case_id':cid,'error':str(exc)})
            print(f'{cid}: ERROR | {exc}')
    out=Path(args.json_out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'\nJSON report written to {out}')

if __name__=='__main__': asyncio.run(main())
