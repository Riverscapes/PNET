---
title: Numerical CSV Template
weight: 2
---

This CSV is used as an input for Step 9, as well as the Outlier Finder Script. This CSV can be found under the Other_Scripts folder once PNET is downloaded. Make sure to not change the column names, as the R script depends on them being the same.

- **PNET Field**
  - This is the column where you can list all of the PNET fields you want to compare. This means any fields that come from any input data networks, or PNET itself (like D50). 
- **PIBO Field**
  - This is the column where you can enter any fields from PIBO (or other field sources)
- **Name**
  - This is the column where you need to enter the name of each comparison. So if the PNET field was [BFWIDTH] and the PIBO field was [Bf], I would want the comparison between the two to be called [Bankfull]. Just make sure that all of the Names are unique within the first 7 characters, as they get truncated in the process. If it gets too difficult to come up with unique identifiers, numbers or codes could also be used.
- **PNET_Valid and Field Valid**
  - This is the column where you need to enter whether or not zeroes are valid numbers for that specific field. For some fields, like proportions, zeroes count as valid data points. However, for a value like Bankful width, a 0 is invalid. Put an 'N' if zeroes are not valid, and a 'Y' if they are valid. Make sure that this column is entirely filled out before running