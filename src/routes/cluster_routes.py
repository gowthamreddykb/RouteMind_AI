from flask import Blueprint, render_template, jsonify
from src.services.clustering_service import ClusteringService

cluster_bp = Blueprint('cluster_bp', __name__)

@cluster_bp.route('/')
def cluster_dashboard():
    clusters = ClusteringService.get_lane_clusters()
    return render_template('cluster_dashboard.html', clusters=clusters)

@cluster_bp.route('/api/clusters')
def api_clusters():
    return jsonify(ClusteringService.get_lane_clusters())
