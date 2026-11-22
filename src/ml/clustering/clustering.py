from src.services.clustering_service import ClusteringService

def cluster_lanes():
    return ClusteringService.get_lane_clusters()
