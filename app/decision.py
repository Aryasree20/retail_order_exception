import re
from .schemas import CaseReport, EvidenceItem, Recommendation
from .data import read_policy

CLAUSES={'window':'P1','damage':'P2','delivery':'P3','cancel':'P4','money':'P5','missing':'P6'}

def decide(packet: dict) -> CaseReport:
    c=packet['case']; o=packet.get('order'); cid=c['case_id']; oid=c.get('order_id')
    evidence=[]; clauses=[]; intent='unknown'; rec=Recommendation.MANUAL_REVIEW; note='Deterministic local review; no LLM facts are treated as authoritative.'
    if not o:
        evidence.append(EvidenceItem(source='data/cases.csv',reference=f"case_id={cid}",fact=f"Request references unknown order {oid}.",kind='verified_fact'))
        clauses=['P6']; rec=Recommendation.REQUEST_INFO; intent='order_lookup'
        return CaseReport(case_id=cid,order_id=oid,detected_intent=intent,verified_order_status=None,within_return_window=None,replacement_stock_available=None,recommendation=rec,evidence=evidence,policy_clause=clauses,confidence_note=note,needs_human_approval=True,explanation='The order ID was not found in the supplied order records. Ask the customer to confirm the order ID; no order facts were inferred.')
    policy_missing=bool(packet.get('errors')) or not packet.get('policy_summary') or packet.get('policy_summary')=='Policy unavailable'
    for field in ('order_id','item','total_inr','order_status','payment_status'):
        evidence.append(EvidenceItem(source='data/orders.csv',reference=f"{field}={o.get(field)}",fact=f"Recorded {field}: {o.get(field)}.",kind='verified_fact'))
    stock=packet.get('inventory') or {}; available=stock.get('replacement_stock')
    if available is not None: evidence.append(EvidenceItem(source='data/inventory.csv',reference=f"item={o['item']}",fact=f"Replacement stock recorded: {available}.",kind='tool_observation'))
    text=c['request_text'].lower(); status=o['order_status']; within=packet.get('within_return_window')
    if policy_missing:
        rec=Recommendation.MANUAL_REVIEW; clauses=['P6']; intent='policy_unavailable'; explanation='The return policy file is missing or unreadable. Eligibility cannot be assumed; route to a human reviewer.'
    elif status=='CANCELLED' and o['payment_status']=='CAPTURED':
        intent='cancelled_but_charged'; rec=Recommendation.REFUND_REVIEW; clauses=['P4','P5']; explanation='The order is recorded as cancelled while payment is captured. Verify the payment transaction and review a refund; no refund has been executed.'
    elif ('delivered' in text and ('never received' in text or 'not received' in text)) or ('where is' in text) or (status=='SHIPPED' and not o.get('delivered_at')):
        intent='delivery_dispute' if 'never received' in text or 'not received' in text else 'delivery_status'; rec=Recommendation.INVESTIGATE_DELIVERY; clauses=['P3']; explanation='The customer delivery concern must be investigated. A delivery/shipping status alone does not authorize an automatic refund.'
        if 'never received' in text or 'not received' in text: evidence.append(EvidenceItem(source='data/cases.csv',reference=f'case_id={cid}',fact='Customer claims the order was not received.',kind='customer_claim'))
    elif 'damage' in text or 'damaged' in text:
        intent='damaged_item'; clauses=['P1','P2','P5']
        if within is True and available is not None and available > 0: rec=Recommendation.REPLACE_REVIEW; explanation='The damage request is within the 30-day window and replacement stock is recorded. Recommend replacement review with human approval.'
        elif within is True: rec=Recommendation.REFUND_REVIEW; explanation='The damage request is within the return window, but replacement stock is unavailable or unverified. Send for human review of an alternative resolution.'
        else: rec=Recommendation.MANUAL_REVIEW; explanation='Damage is claimed, but the return-window evidence is missing or outside the standard window. Human review is required.'
    elif '50000' in text or (re.search(r'(?:inr|rs\.?|₹)\s*([\d,]+)',text) and int(re.sub(r'\D','',re.search(r'(?:inr|rs\.?|₹)\s*([\d,]+)',text).group(1))) != int(o['total_inr'])):
        intent='refund_amount_mismatch'; rec=Recommendation.MANUAL_REVIEW; clauses=['P5','P6']; evidence.append(EvidenceItem(source='data/cases.csv',reference=f'case_id={cid}',fact='Customer requested amount differs from the recorded order total.',kind='customer_claim')); explanation=f"The requested refund amount does not match the recorded order total of INR {o['total_inr']}. Verify the claim and payment records manually; no transaction is performed."
    elif 'cancel' in text and status in ('PROCESSING','SHIPPED'):
        intent='cancellation_request'; rec=Recommendation.MANUAL_REVIEW; clauses=['P5','P6']; explanation='The customer requests cancellation, but this assignment has no cancellation tool or authority to change order status. Refer for manual review.'
    elif within is False:
        intent='return_request'; rec=Recommendation.NOT_ELIGIBLE; clauses=['P1']; explanation=f"The request is {packet.get('days_after_delivery')} calendar days after confirmed delivery, beyond the inclusive 30-day standard window. No approved exception is present in the supplied records."
    elif within is True:
        intent='return_eligibility'; rec=Recommendation.REFUND_REVIEW; clauses=['P1','P5']; explanation='The request falls within the inclusive 30-day return window. A human must review and approve any refund; no payment action is performed.'
    else:
        intent='insufficient_delivery_evidence'; rec=Recommendation.REQUEST_INFO; clauses=['P6']; explanation='The supplied records do not contain a confirmed delivery date needed to assess return eligibility. Request delivery confirmation or additional information.'
    if within is not None: evidence.append(EvidenceItem(source='data/orders.csv + data/cases.csv',reference=f"delivered_at={o.get('delivered_at')}; request_date={c['request_date']}",fact=f"Request is {packet.get('days_after_delivery')} calendar days after delivery; within inclusive 30-day window: {within}.",kind='verified_fact'))
    return CaseReport(case_id=cid,order_id=oid,detected_intent=intent,verified_order_status=status,within_return_window=within,replacement_stock_available=None if available is None else available>0,recommendation=rec,evidence=evidence,policy_clause=clauses,confidence_note=note,needs_human_approval=True,explanation=explanation)
