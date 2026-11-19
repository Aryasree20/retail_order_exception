import csv
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

def read_csv(name):
    with (DATA / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def load_case(case_id):
    rows = read_csv('cases.csv')
    matches = [r for r in rows if r.get('case_id') == case_id]
    if not matches:
        raise KeyError(f'Unknown case_id: {case_id}')
    return matches[0]

def lookup_order(order_id):
    return next((r for r in read_csv('orders.csv') if r.get('order_id') == order_id), None)

def lookup_stock(item):
    row = next((r for r in read_csv('inventory.csv') if r.get('item','').casefold() == str(item).casefold()), None)
    return None if row is None else int(row['replacement_stock'])

def read_policy():
    p = DATA / 'return_policy.md'
    if not p.is_file():
        raise FileNotFoundError('data/return_policy.md is missing')
    return p.read_text(encoding='utf-8')

def window_status(order, request_date):
    if not order or not order.get('delivered_at'):
        return None, None
    delivered = date.fromisoformat(order['delivered_at'])
    requested = date.fromisoformat(request_date)
    days = (requested - delivered).days
    return 0 <= days <= 30, days
