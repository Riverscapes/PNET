---
title: Step 8
weight: 8
---

The eighth step in PNET is to collect all extracted field reaches and merge them into one shapefile containing all data for that entire watershed. The inputs for this tool are:



- Root Folder



  This tool is simple. For every watershed, field reaches with extracted data are merged together into one watershed-wide collection of field reaches. Each field reach will now contain all data from every data network. 

This tool assumes that there are multiple data networks to join. There may be unexpected results if that isn’t the case. If it is possible to somehow tag each field with the data network originated from, that would be great. This can be done with an AddJoin, but outputting results in that way has been difficult. Another option to be added could be summarizing the data in a point shapefile as opposed to networks. Th