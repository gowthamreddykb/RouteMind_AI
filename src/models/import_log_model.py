import datetime as dt
from extensions import db

class ShipmentImportLog(db.Model):
    __tablename__ = 'import_logs'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    total_rows = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    rejected_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='SUCCESS')
    error_summary = db.Column(db.Text, nullable=True)
    imported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    imported_by_name = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'total_rows': self.total_rows,
            'success_count': self.success_count,
            'rejected_count': self.rejected_count,
            'status': self.status,
            'error_summary': self.error_summary,
            'imported_by_name': self.imported_by_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
