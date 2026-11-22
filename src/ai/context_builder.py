def build_context(shipment, scores=None):
    return {
        'shipment_id': shipment.get('shipment_id'),
        'mode': shipment.get('shipping_mode'),
        'scheduled_days': shipment.get('scheduled_days'),
        'warehouse_time': shipment.get('warehouse_time'),
        'region': shipment.get('region'),
        'scores': scores or {}
    }
