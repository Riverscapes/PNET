---
title: Step 5
weight: 5
---

The fifth step in PNET is to clean up the field points and reaches.

- **Project Folder**
  - This is the folder that contains all data for the project. Folders with the prefix "00_" will be ignored.

This tool is rather simple. It takes the outputs from step 4, and cleans them up. First, a field called “FldRchLen” is added. This field contains the length of the field reach that was generated in step 4. Next, all TOR field points are deleted, leaving only the BOR points. This is done as having two points now is superfluous. After that, we make sure that all points share all the data present on the corresponding field reach, and vice versa. Finally, all fields not pertaining to PNET analysis are removed.