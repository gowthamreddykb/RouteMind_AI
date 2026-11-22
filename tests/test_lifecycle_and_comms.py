import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from src.app import create_app
from extensions import db
from src.models.user_model import User
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.communication_model import CommunicationLog

def test_full_lifecycle_and_comms():
    app = create_app('config.DevelopmentConfig')
    with app.app_context():
        client = app.test_client()
        
        # 1. Setup users
        dispatcher = User.query.filter_by(username='dispatcher').first()
        manager = User.query.filter_by(username='manager').first()
        admin = User.query.filter_by(username='admin').first()
        
        # 2. Test Communication Hub GET
        client.get('/auth/quick-login/dispatcher', follow_redirects=True)
            
        r_comm = client.get('/communications/', follow_redirects=True)
        assert r_comm.status_code == 200, f"Expected 200, got {r_comm.status_code}"
        assert 'Consignment Communication Drafts' in r_comm.get_data(as_text=True)
        print("Communication Hub GET for Dispatcher PASSED.")
        
        # 3. Test Dispatcher Submitting Draft
        r_sub = client.post('/communications/api/submit-draft', data={
            'shipment_id': '1',
            'recipient': 'test@client.com',
            'subject': 'Draft Advisory',
            'body': 'This is a test draft.'
        }, follow_redirects=True)
        assert r_sub.status_code == 200
        print("Dispatcher submit draft PASSED.")
        
        # 4. Test Manager Reviewing and Approving
        client.get('/auth/quick-login/manager', follow_redirects=True)
            
        r_comm_mgr = client.get('/communications/')
        assert r_comm_mgr.status_code == 200
        assert 'Communication Approval Hub' in r_comm_mgr.get_data(as_text=True)
        
        r_appr = client.post('/communications/api/approve', data={
            'shipment_id': '1',
            'recipient': 'test@client.com',
            'subject': 'Approved Advisory',
            'body': 'Approved by manager.'
        }, follow_redirects=True)
        print('Manager approve status:', r_appr.status_code)
        assert r_appr.status_code == 200
        print("Manager approve and dispatch PASSED.")
        
        # 5. Test Delivery Confirmation
        s = Shipment.query.first()
        old_status = s.order_status
        r_deliv = client.post(f'/shipments/{s.id}/confirm-delivery', data={
            'delivery_confirmation_ref': 'POD-VERIFY-99',
            'notes': 'Verified at terminal gate.'
        })
        print("Delivery post status:", r_deliv.status_code, "Location:", r_deliv.headers.get('Location'))
        db.session.expire_all()
        s = db.session.get(Shipment, s.id)
        print("Shipment status after delivery confirmation:", s.order_status)
        assert s.order_status == 'DELIVERED'
        print("Delivery Confirmation PASSED.")
        
        # 6. Test Shipment Completion (Blocked if open exceptions exist)
        # Add open exception to test gating
        ex = ShipmentException(shipment_id=s.id, exception_type='CUSTOMS_INSPECTION', severity='HIGH', status='OPEN')
        db.session.add(ex)
        db.session.commit()
        
        r_comp_blocked = client.post(f'/shipments/{s.id}/complete', follow_redirects=True)
        db.session.expire_all()
        s = db.session.get(Shipment, s.id)
        assert s.order_status == 'DELIVERED', "Completion must be blocked when open exceptions exist!"
        print("Completion gating on open exceptions PASSED.")
        
        # Resolve exception
        ex.status = 'RESOLVED'
        db.session.commit()
        
        # Now complete shipment
        r_comp = client.post(f'/shipments/{s.id}/complete', follow_redirects=True)
        assert r_comp.status_code == 200
        db.session.expire_all()
        s = db.session.get(Shipment, s.id)
        assert s.order_status == 'COMPLETED'
        print("Shipment Completion PASSED.")
        
        # Clean up
        db.session.delete(ex)
        s.order_status = old_status
        db.session.commit()
        print("Full Lifecycle & Comms Test COMPLETED SUCCESSFULLY!")

if __name__ == '__main__':
    test_full_lifecycle_and_comms()
