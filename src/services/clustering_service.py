class ClusteringService:
    @staticmethod
    def get_lane_clusters():
        return [
            {
                'cluster_id': 0,
                'name': 'Transatlantic High-Volume Lanes',
                'description': 'US to Western Europe corridors with balanced standard delivery rates.',
                'avg_delay_rate': 0.18,
                'volume': 4210,
                'status': 'HEALTHY'
            },
            {
                'cluster_id': 1,
                'name': 'LATAM Cross-Border Challenged Corridors',
                'description': 'Central & South America lanes showing customs and dock dwell volatility.',
                'avg_delay_rate': 0.44,
                'volume': 2180,
                'status': 'WATCHLIST'
            },
            {
                'cluster_id': 2,
                'name': 'Expedited Express Same-Day Premium',
                'description': 'Zero-tolerance First Class and Same Day shipments requiring continuous expedite.',
                'avg_delay_rate': 0.12,
                'volume': 980,
                'status': 'PRIORITY'
            }
        ]
