data "azurerm_resource_group" "project_rg_shared" {
  name = var.shared_project_resource_group_name
}

data "azurerm_storage_account" "existing" {
  name                = var.shared_storage_account_name
  resource_group_name = data.azurerm_resource_group.project_rg_shared.name
}

data "azurerm_service_plan" "existing" {
  name                = var.app_service_plan_name
  resource_group_name = var.asp_resource_group_name
}

data "azurerm_storage_queue" "fetch_queue" {
  name                = var.fetch_queue_name
  storage_account_name = data.azurerm_storage_account.existing.name
}

data "azurerm_log_analytics_workspace" "existing" {
  name                = var.log_analytics_workspace_name
  resource_group_name = var.law_resource_group_name
}

data "azurerm_mysql_flexible_server" "existing" {
  name                = var.mysql_server_name
  resource_group_name = var.mysql_server_resource_group_name
}

resource "azurerm_application_insights" "main" {
  name                = var.service_name
  resource_group_name = data.azurerm_resource_group.project_rg_shared.name
  location            = data.azurerm_resource_group.project_rg_shared.location
  application_type    = "web"
  workspace_id        = data.azurerm_log_analytics_workspace.existing.id
}

# Create production MySQL database
resource "azurerm_mysql_flexible_database" "prod" {
  name                = var.service_name
  resource_group_name = data.azurerm_mysql_flexible_server.existing.resource_group_name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Create staging MySQL database
resource "azurerm_mysql_flexible_database" "stage" {
  name                = "${var.service_name}-stage"
  resource_group_name = data.azurerm_mysql_flexible_server.existing.resource_group_name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Generate random passwords for database users
resource "random_password" "prod_db_password" {
  length  = 32
  special = true
}

resource "random_password" "stage_db_password" {
  length  = 32
  special = true
}

# Create MySQL user for production with read access
resource "mysql_user" "prod_user" {
  user               = "${var.service_name}_user"
  host               = "%"
  plaintext_password = random_password.prod_db_password.result
}

# Create MySQL user for staging with read access
resource "mysql_user" "stage_user" {
  user               = "${var.service_name}_stage_user"
  host               = "%"
  plaintext_password = random_password.stage_db_password.result
}

# Grant read permissions to production user
resource "mysql_grant" "prod_grant" {
  user       = mysql_user.prod_user.user
  host       = mysql_user.prod_user.host
  database   = azurerm_mysql_flexible_database.prod.name
  privileges = ["SELECT", "SHOW VIEW"]
}

# Grant read permissions to staging user
resource "mysql_grant" "stage_grant" {
  user       = mysql_user.stage_user.user
  host       = mysql_user.stage_user.host
  database   = azurerm_mysql_flexible_database.stage.name
  privileges = ["SELECT", "SHOW VIEW"]
}


resource "azurerm_linux_function_app" "function_app" {
  name                       = var.service_name
  resource_group_name        = data.azurerm_resource_group.project_rg_shared.name
  location                   = data.azurerm_resource_group.project_rg_shared.location
  service_plan_id            = data.azurerm_service_plan.existing.id
  storage_account_name       = data.azurerm_storage_account.existing.name
  storage_account_access_key = data.azurerm_storage_account.existing.primary_access_key

  site_config {
    always_on        = true
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version = "3.12"
    }
  }


  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"     = "1"
    "FETCH_QUEUE_NAME"             = data.azurerm_storage_queue.fetch_queue.name
    "SQLALCHEMY_CONNECTION_STRING" = "mysql+pymysql://${mysql_user.prod_user.user}:${random_password.prod_db_password.result}@${data.azurerm_mysql_flexible_server.existing.fqdn}:3306/${azurerm_mysql_flexible_database.prod.name}?charset=utf8mb4&ssl_disabled=false&ssl_verify_cert=true"
  }

  sticky_settings {
    app_setting_names = [
      "FETCH_QUEUE_NAME",
      "SQLALCHEMY_CONNECTION_STRING"
    ]
  }
}

resource "azurerm_linux_function_app_slot" "staging_slot" {
  name                       = "stage"
  function_app_id            = azurerm_linux_function_app.function_app.id
  storage_account_name       = data.azurerm_storage_account.existing.name
  storage_account_access_key = data.azurerm_storage_account.existing.primary_access_key

  site_config {
    always_on        = true
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"     = "1"
    "FETCH_QUEUE_NAME"             = "${data.azurerm_storage_queue.fetch_queue.name}-stage"
    "SQLALCHEMY_CONNECTION_STRING" = "mysql+pymysql://${mysql_user.stage_user.user}:${random_password.stage_db_password.result}@${data.azurerm_mysql_flexible_server.existing.fqdn}:3306/${azurerm_mysql_flexible_database.stage.name}?charset=utf8mb4&ssl_disabled=false&ssl_verify_cert=true"
  }
}
