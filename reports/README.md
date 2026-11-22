# RouteMind AI: EDA reports index

Start with `final_summary/final_report.md`.

- `data_quality/` : data_quality_issues.csv, report.md
- `data_understanding/` : data_dictionary.csv, report.md
- `feature_availability/` : matrix_model1_order_creation.csv, matrix_model2_dispatch.csv, missing_dispatch_fields.csv, report.md
- `feature_discovery/` : feature_candidates.csv, report.md
- `final_summary/` : final_report.md, ranked_feature_table.csv
- `leakage_audit/` : leakage_register.csv, report.md
- `patterns/access_logs/` : report.md
- `patterns/advanced_analysis/` : 01_cluster_late_rate.png, association_ranking.csv, association_rules_top.csv, distribution_outliers.csv, kmeans_clusters.csv, report.md, residual_signal_search.csv
- `patterns/correlation/` : 01_pearson_heatmap.png, 02_spearman_heatmap.png, 03_selected_scatter.png, 04_correlation_comparison.png, redundant_pairs.csv, report.md, target_correlations.csv
- `patterns/customer_history/` : 01_customer_frequency.png, 02_customer_late_distribution.png, 03_top_customers.png, 04_late_by_prior_orders.png, report.md
- `patterns/geography/` : 01_country_distribution.png, 02_region_late_rate.png, 03_top_city_volume.png, 03_top_state_volume.png, 04_top_city_late_rate.png, 04_top_state_late_rate.png, 05_region_mode_heatmap.png, city_rates.csv, country_rates.csv, market_rates.csv, region_rates.csv, report.md, state_rates.csv
- `patterns/historical_delivery/` : 01_history_signal.png, 02_mode_over_time.png, 03_region_history.png, 04_customer_group.png, history_feature_summary.csv, report.md
- `patterns/late_delivery/` : 01_late_donut.png, 02_status_bar.png, 03_severity_bar.png, 04_delay_hist.png, 05_monthly_late.png, 06_actual_vs_sched.png, 07_volume_over_time.png, report.md
- `patterns/multivariate/` : A_region_mode.csv, A_region_mode.png, A_region_mode_table.csv, B_quantity_mode.csv, B_quantity_mode.png, B_quantity_mode_table.csv, C_value_mode.csv, C_value_mode.png, C_value_mode_table.csv, D_noon_mode.csv, D_noon_mode.png, D_noon_mode_table.csv, E_segment_mode.csv, E_segment_mode.png, E_segment_mode_table.csv, F_month_market.csv, F_month_market.png, F_month_market_table.csv, G_volume_market.csv, G_volume_market.png, G_volume_market_table.csv, H_category_market.csv, H_category_market.png, H_category_market_table.csv, report.md
- `patterns/order_priority/` : report.md
- `patterns/order_quantity/` : 01_quantity_hist.png, 02_order_size_distribution.png, 03_late_by_size.png, 04_qty_vs_delay.png, qty_group_rates.csv, report.md
- `patterns/order_value/` : 01_value_hist.png, 02_value_boxplot.png, 03_late_by_value.png, 04_value_vs_delay.png, report.md, value_quartile_rates.csv
- `patterns/order_volume/` : 01_daily_monthly_volume.png, 02_region_volume.png, 03_volume_vs_late.png, 04_high_volume_comparison.png, region_volume.csv, report.md
- `patterns/origin_destination/` : 01_proxy_heatmap.png, 02_proxy_top_pairs.png, report.md, route_proxy_rates.csv
- `patterns/product_category/` : 01_category_distribution.png, 02_category_late_rate.png, 03_top_products.png, 04_category_mode_heatmap.png, category_rates.csv, product_rates.csv, report.md
- `patterns/scheduled_shipping/` : 01_scheduled_distribution.png, 02_actual_vs_scheduled.png, 03_late_by_scheduled.png, 04_scheduled_vs_actual_scatter.png, 05_region_scheduled_heatmap.png, report.md, scheduled_rates.csv
- `patterns/shipping_mode/` : 01_mode_distribution.png, 02_mode_late_rate.png, 03_mode_actual_vs_sched.png, 04_mode_severity_heatmap.png, mode_severity.csv, mode_summary.csv, report.md
- `patterns/time_based/` : 01_monthly_volume.png, 02_monthly_late_rate.png, 03_weekday_orders.png, 04_weekday_late_rate.png, 05_hourly_orders.png, 06_hourly_late_rate.png, 07_weekly_trend.png, 08_mode_noon_cutoff.png, hour_by_mode.csv, hour_rates.csv, month_rates.csv, monthly_rates.csv, quarter_rates.csv, report.md, weekday_rates.csv, year_rates.csv