import numpy as np

class AnomalyService:
    @staticmethod
    def detect_anomalies(shipments_data):
        # Isolation forest / statistical heuristic anomaly check
        anomalies = []
        for s in shipments_data:
            sched = s.get('scheduled_days', 4)
            wh = s.get('warehouse_time', 2.0)
            sales = s.get('sales', 100.0)
            qty = s.get('quantity', 1)
            
            reasons = []
            score = 0.1
            if wh > sched:
                reasons.append(f'Warehouse duration ({wh}d) exceeds entire scheduled SLA window ({sched}d)')
                score += 0.5
            if sales / max(qty, 1) > 1000:
                reasons.append(f'Abnormal high unit price anomaly (${sales/qty:.2f})')
                score += 0.25
            if sched == 0 and wh > 0.5:
                reasons.append('Same-day shipment missing immediate dispatch window')
                score += 0.4
                
            if score >= 0.5:
                anomalies.append({
                    'shipment_id': s.get('shipment_id', 'UNKNOWN'),
                    'anomaly_score': min(score, 0.99),
                    'reasons': reasons,
                    'severity': 'HIGH' if score >= 0.75 else 'MEDIUM'
                })
        return anomalies
