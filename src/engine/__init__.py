"""Market State Engine (Hari 2).

Responsibilities:
- Filter exclusion of financial sectors (banks, insurance, multifinance)
- Calculate 8 core financial metrics
- Statistical normalization via Winsorizing (1%/99%), Median, and MAD
- Construct CompanyState records with peer_z scores
"""
