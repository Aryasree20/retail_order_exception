from datetime import date
from .runnables import RunnableLambda, RunnableParallel, RunnableBranch
from .data import load_case, lookup_order, lookup_stock, read_policy, window_status
from .schemas import EvidencePacket

def _load(case_id):
    case = load_case(case_id)
    order = lookup_order(case.get('order_id'))
    errors = []
    try: policy = read_policy()
    except OSError as e:
        policy = ''
        errors.append(str(e))
    within, days = window_status(order, case['request_date'])
    return {'case_id': case_id, 'case': case, 'order': order, 'policy': policy, 'within': within, 'days': days, 'errors': errors}

def _policy(x):
    policy = x['policy']
    if not policy: return {'policy_summary':'Policy unavailable'}
    clauses = [line.strip() for line in policy.splitlines() if line.startswith('## Clause')]
    return {'policy_summary': '; '.join(clauses)}

def _order(x):
    o=x['order']
    return {'order_facts': None if not o else {k:o.get(k) for k in ('order_id','item','total_inr','delivered_at','order_status','payment_status')}}

def _inventory(x):
    o=x['order']
    return {'inventory_facts': None if not o else {'item':o['item'],'replacement_stock':lookup_stock(o['item'])}}

# RunnableParallel deliberately gathers independent policy, order and stock evidence.
_parallel = RunnableParallel(policy=_policy, order=_order, inventory=_inventory)

def _assemble(x):
    parallel = _parallel.invoke(x)
    inv=parallel['inventory']['inventory_facts']
    packet=EvidencePacket(case_id=x['case_id'], case=x['case'], order=x['order'],
        policy_summary=parallel['policy']['policy_summary'], inventory=inv,
        within_return_window=x['within'], days_after_delivery=x['days'], errors=x['errors'])
    return packet.model_dump()

# Branch component is used for explicit intent routing metadata; deterministic decisions live in rules.py.
def _route_delivery(x): return 'delivery' in x['case']['request_text'].lower() or 'never received' in x['case']['request_text'].lower() or 'where is' in x['case']['request_text'].lower()
def _route_cancel(x): return 'cancel' in x['case']['request_text'].lower()
_router = RunnableBranch((_route_delivery, RunnableLambda(lambda x: {**x,'route':'delivery'})),
                         (_route_cancel, RunnableLambda(lambda x: {**x,'route':'cancellation'})),
                         RunnableLambda(lambda x: {**x,'route':'returns_or_damage'}))

pipeline = RunnableLambda(_load) | RunnableLambda(_assemble) | _router | RunnableLambda(lambda x: EvidencePacket(**{k:v for k,v in x.items() if k in EvidencePacket.model_fields}).model_dump())
