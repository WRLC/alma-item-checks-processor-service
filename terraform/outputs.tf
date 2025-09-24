output "function_app_name" {
  description = "The name of the main Function App."
  value       = azurerm_linux_function_app.function_app.name
}

output "function_app_resource_group_name" {
  description = "The resource group of the function app."
  value       = azurerm_linux_function_app.function_app.resource_group_name
}

output "prod_db_name" {
  description = "The name of the production database."
  value       = azurerm_mysql_flexible_database.prod.name
}

output "prod_db_user" {
  description = "The username for the production database managed identity."
  value       = azurerm_linux_function_app.function_app.name
}

output "stage_db_name" {
  description = "The name of the stage database."
  value       = azurerm_mysql_flexible_database.stage.name
}

output "stage_db_user" {
  description = "The username for the stage database managed identity."
  value       = "${azurerm_linux_function_app.function_app.name}-stage"
}

output "python_version" {
  description = "The Python version used for the Function App"
  value       = azurerm_linux_function_app.function_app.site_config[0].application_stack[0].python_version
}

output "stage_slot_name" {
  description = "The name of the app's staging deployment slot"
  value       = azurerm_linux_function_app_slot.staging_slot.name
}
