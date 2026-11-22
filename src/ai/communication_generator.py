from src.ai.prompt_templates import CARRIER_SLA_TEMPLATE

def generate_carrier_notice(shipment_data, risk_data):
    return CARRIER_SLA_TEMPLATE.format(
        shipment_id=shipment_data.get('shipment_id', 'UNKNOWN'),
        origin=shipment_data.get('origin', 'Warehouse Hub 1'),
        destination=shipment_data.get('destination', 'Western Europe'),
        scheduled_days=shipment_data.get('scheduled_days', 4),
        warehouse_time=shipment_data.get('warehouse_time', 2.0),
        risk_percentage=risk_data.get('risk_percentage', 50.0),
        risk_level=risk_data.get('risk_level', 'MEDIUM'),
        action=risk_data.get('action', 'Immediate dock release')
    )
