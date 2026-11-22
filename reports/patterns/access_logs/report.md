# Access-log analysis (tokenized_access_logs.csv)


## Status: not performed

`tokenized_access_logs.csv` was **not uploaded** (the upload folder holds only `DataCoSupplyChainDataset.csv`). No log statistics, graphs or conclusions are produced: **Insufficient data**.


## What would be analysed once the file is supplied

Product/category/department browsing frequency, URL frequency, hourly and daily activity, IP-level activity, repeated browsing and, if event order is reliable, sequences.


## Relationship to shipment prediction

DataCo's shipment data has **no IP address, session id, URL or shared key**. Without a shared identifier and event timestamps proving availability before order creation, access logs must stay separate and cannot be a shipment-prediction feature.
