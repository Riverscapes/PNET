library(car)
library(MASS)

# Clean workspace
rm(list = ls())

# Set working Directory
setwd("C:\\Users\\Tyler\\Desktop\\Work\\Test_Run\\00_Scripttesting")

# Add in data from PNET output
all_data = read.csv("All_Data.csv")
fields =read.csv("R_Fields_Template.csv", fileEncoding="UTF-8-BOM")
export_list = list()

for (row in 1:nrow(fields)){
  pnet_field = lapply((fields[row, "pnet"]), as.character)[[1]]
  pibo_field = lapply((fields[row, "pibo"]), as.character)[[1]]
  new_name = lapply((fields[row, "newname"]), as.character)[[1]]
  
  analysis = all_data[, c("RchID", pnet_field, pibo_field)]
  fit <- lm(analysis[,2]~analysis[,3]) 
  fit_res = studres(fit)
  fit_res_df = cbind(read.table(text = names(fit_res)), fit_res)
  new_data = cbind(analysis, fit_res_df)
  outliers = new_data[abs(new_data$fit_res) > 2,]
  outlier_id = outliers$RchID
  message(paste(new_name, "Outliers"))
  for (reach in outlier_id){
    message(paste("\"RchID\" = ", reach, " OR"))
  }
  
  export_list[[pnet_field]] = outlier_id
  export_list[[pibo_field]] = outlier_id
  
  write.table(export_list[pnet_field], 'Outliers.csv'  , append= T, sep=',' )
  write.table(export_list[pibo_field], 'Outliers.csv'  , append= T, sep=',' )
}


