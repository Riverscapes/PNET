---
title: Step 8b
weight: 8
---

This opional step allows D50 estimations to be calculated based on data from input data networks.



- **Project Folder**

  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.

    

To calculate D50, this tool requires several fields to already be in the data (from input data netoworks). It requires a discharge field [iHyd_Q2], a bankfull field [BFWIDTH], and a slope field ["iGeo_Slope"].  For each watershed, two fields are created to hold D50 estimates.

[PredD50_03] : Calulated using n=.035 and tc = .03

[PredD50_04] : Calulated using n=.035 and tc = .04

The equation used to calculate is as follows:

```python
((997 * 9.81) * n * ((discharge-.0283168) ** (3/5)) * (bankfull ** (-3/5)) * (slope ** (7/10))) / ((2650-997) * 9.81 * tc)
```