import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from src.app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.routes.shipment_routes import build_milestone_cycle

def test_milestone_cycle():
    app = create_app('config.DevelopmentConfig')
    with app.app_context():
        s = Shipment.query.first()
        print(f"Testing shipment: ID={s.id}, Number={s.shipment_number}, Status={s.order_status}")
        
        cycle = build_milestone_cycle(s)
        assert len(cycle) == 9, f"Expected 9 milestones, got {len(cycle)}"
        
        expected_keys = [
            'CREATED',
            'BOOKING_CONFIRMED',
            'READY_FOR_DISPATCH',
            'DISPATCHED',
            'IN_TRANSIT',
            'ARRIVED_AT_DESTINATION',
            'OUT_FOR_DELIVERY',
            'DELIVERED',
            'COMPLETED'
        ]
        
        for idx, m in enumerate(cycle):
            print(f"[{m['step']}] {m['key']} -> State: {m['state']} (TS: {m['timestamp']})")
            assert m['step'] == idx + 1
            assert m['key'] == expected_keys[idx]
            assert m['state'] in ['done', 'current', 'pending']

        # Test HTTP GET rendered page
        client = app.test_client()
        dispatcher = User.query.filter_by(username='dispatcher').first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dispatcher.id)
            sess['_fresh'] = True

        resp = client.get(f'/shipments/{s.id}')
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        html = resp.get_data(as_text=True)
        
        assert 'Consignment Milestone Progress' in html
        for idx, key in enumerate(expected_keys, 1):
            assert f"{idx}. {key}" in html, f"Missing milestone {idx}. {key} in HTML"
        print("\nAll 9 milestones correctly rendered in HTML!")

        # Test status update endpoint
        old_status = s.order_status
        resp_post = client.post(f'/shipments/{s.id}/update-status', data={
            'status': 'ARRIVED_AT_DESTINATION',
            'notes': 'Vessel safely berthed at destination quay.'
        }, follow_redirects=True)
        assert resp_post.status_code == 200
        
        db.session.refresh(s)
        assert s.order_status == 'ARRIVED_AT_DESTINATION'
        
        updated_cycle = build_milestone_cycle(s)
        # Step 6 is ARRIVED_AT_DESTINATION -> state should be 'current'
        assert updated_cycle[5]['state'] == 'current'
        # Steps 1 to 5 should be 'done'
        for i in range(5):
            assert updated_cycle[i]['state'] == 'done'
        # Steps 7 to 9 should be 'pending'
        for i in range(6, 9):
            assert updated_cycle[i]['state'] == 'pending'
            
        print("Milestone transition verified successfully!")
        
        # Restore status
        s.order_status = old_status
        db.session.commit()
        print("Restored original shipment status.")

if __name__ == '__main__':
    test_milestone_cycle()
