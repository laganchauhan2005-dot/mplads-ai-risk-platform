# MPLADS Data Audit — Initial Findings

## Source coverage
10 CSV files are available: 5 Lok Sabha and 5 Rajya Sabha datasets.

## Row counts

| Dataset | Rows |
|---|---:|
| Lok Sabha — Allocated Limit | 544 |
| Lok Sabha — Works Recommended | 106,440 |
| Lok Sabha — Works Sanctioned | 79,083 |
| Lok Sabha — Works Completed | 34,276 |
| Lok Sabha — Expenditure | 83,981 |
| Rajya Sabha — Allocated Limit | 232 |
| Rajya Sabha — Works Recommended | 25,186 |
| Rajya Sabha — Works Sanctioned | 19,565 |
| Rajya Sabha — Works Completed | 9,957 |
| Rajya Sabha — Expenditure | 25,119 |

## Key findings

- The sanctioned datasets contain one summary/footer row (`Grand Total`) and it must be excluded from project-level analysis.
- Work IDs can be normalized from the Work fields and provide the best project-level join key.
- Recommended datasets contain many rows without a usable Work ID; artificial IDs should not be created.
- Expenditure is one-to-many and must be aggregated by Work ID before joining.
- Missing completion/expenditure records are not automatically anomalies.
- No analytical sanctioned project was found with recommendation date after sanction date.
- No completed project was found with completion date before sanction date.
- No Lok Sabha analytical project had aggregated expenditure or completed amount above sanction amount.
- One Rajya Sabha project had aggregated expenditure above its sanction amount; this should be retained as an audit flag for investigation, not deleted.
- A small number of recommended/sanction amount mismatches exist and should be investigated before treating the two fields as interchangeable.
- Extreme amounts should be preserved because anomaly detection is a core objective of the project.

## Next step

Use `01_data_audit.ipynb` to reproduce these checks locally, then create `docs/data_dictionary.md` and `docs/data_audit.md` before splitting the ML work between Lagan and Samridhi.
