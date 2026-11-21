import json

def parse_kit_items(raw_items):
    """Safely parse kit items into a list of integer instrument IDs."""
    if raw_items is None:
        return []
    if isinstance(raw_items, str):
        raw_items = raw_items.strip()
        if raw_items.startswith('[') and raw_items.endswith(']'):
            try:
                raw_items = json.loads(raw_items)
            except Exception:
                raw_items = [x.strip() for x in raw_items.strip('[]').split(',') if x.strip()]
        elif ',' in raw_items:
            raw_items = [x.strip() for x in raw_items.split(',') if x.strip()]
        else:
            try:
                raw_items = [int(raw_items)]
            except ValueError:
                raw_items = []
    if isinstance(raw_items, (int, float)):
        return [int(raw_items)]
    if isinstance(raw_items, list):
        res = []
        for x in raw_items:
            try:
                res.append(int(x))
            except (ValueError, TypeError):
                pass
        return res
    return []