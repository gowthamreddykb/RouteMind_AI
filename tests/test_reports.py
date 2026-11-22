import pytest
from src.services.clustering_service import ClusteringService

def test_clustering_service():
    clusters = ClusteringService.get_lane_clusters()
    assert len(clusters) == 3
