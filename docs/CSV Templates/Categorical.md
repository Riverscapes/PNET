---
title: Categorical CSV Template
weight: 2
---

This CSV is used as an input for Step 10. This CSV can be found under the Other_Scripts folder once PNET is downloaded.

- **Metagroup Field**
  - This is the field which you want to metagroup things by. More explanation on metagroups can be found in the Step 10 instructions.
- **Metagroup Name**
  - This is the name of the metagroup. For instance, if the metagroup field is [RS_Type], I may want the name to be 'RiverStyles_Type'.
- **Grouping Field**
  - This is the field which you want to group things by. More explanation on groups can be found in the Step 10 instructions.
- **Grouping Name**
  - This is the name of the group. For instance, if the metagroup field is [geo_cond], I may want the name to be 'GeoCondition'.
- **Y-Axis Fields**
  - Put as many fields as you need to here, as long as they stay in the column. Add a new row for each field. Each row you enter here means one boxplot, grouped by the grouping field.

This CSV can handle many different metagroups and groups. Just a new row with a new group, and it will recognize it as such. Don't add new column headers, those should only be at the very top.