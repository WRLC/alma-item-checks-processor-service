locals {
  service_name = "aic-processor-service"
}

data "terraform_remote_state" "shared" {
  backend = "azurerm"
  config  = {
    resource_group_name: var.tf_shared_resource_group_name
    storage_account_name: var.tf_shared_storage_account_name
    container_name: var.tf_shared_container_name
    key: var.tf_shared_key
  }
}

data "azurerm_service_plan" "existing" {
  name                = data.terraform_remote_state.shared.outputs.app_service_plan_name
  resource_group_name = data.terraform_remote_state.shared.outputs.app_service_plan_resource_group
}

data "azurerm_resource_group" "existing" {
  name = data.terraform_remote_state.shared.outputs.resource_group_name
}

data "azurerm_storage_account" "existing" {
  name                     = data.terraform_remote_state.shared.outputs.storage_account_name
  resource_group_name      = data.terraform_remote_state.shared.outputs.resource_group_name
}

locals {
  storage_queues     = data.terraform_remote_state.shared.outputs.storage_queues
  storage_containers = data.terraform_remote_state.shared.outputs.storage_containers
  storage_tables     = data.terraform_remote_state.shared.outputs.storage_tables
}

data "azurerm_mysql_flexible_server" "existing" {
  name                = data.terraform_remote_state.shared.outputs.mysql_server_name
  resource_group_name = data.terraform_remote_state.shared.outputs.mysql_server_resource_group_name
}

data "azurerm_log_analytics_workspace" "existing" {
  name                = data.terraform_remote_state.shared.outputs.log_analytics_workspace_name
  resource_group_name = data.terraform_remote_state.shared.outputs.log_analytics_workspace_resource_group_name
}

resource "azurerm_application_insights" "main" {
  name                = local.service_name
  resource_group_name = data.azurerm_resource_group.existing.name
  location            = data.azurerm_resource_group.existing.location
  application_type    = "web"
  workspace_id        = data.azurerm_log_analytics_workspace.existing.id
}

# Create production MySQL database
resource "azurerm_mysql_flexible_database" "prod" {
  name                = local.service_name
  resource_group_name = data.azurerm_mysql_flexible_server.existing.resource_group_name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Create staging MySQL database
resource "azurerm_mysql_flexible_database" "stage" {
  name                = "${local.service_name}-stage"
  resource_group_name = data.azurerm_mysql_flexible_server.existing.resource_group_name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Generate random passwords for database users
resource "random_password" "prod_db_password" {
  length  = 32
  special = false
}

resource "random_password" "stage_db_password" {
  length  = 32
  special = false
}

# Create MySQL user for production with read access
resource "mysql_user" "prod_user" {
  user               = "${local.service_name}_user"
  host               = "%"
  plaintext_password = random_password.prod_db_password.result
}

# Create MySQL user for staging with read access
resource "mysql_user" "stage_user" {
  user               = "${local.service_name}_stage_user"
  host               = "%"
  plaintext_password = random_password.stage_db_password.result
}

# Grant read permissions to production user
resource "mysql_grant" "prod_grant" {
  user       = mysql_user.prod_user.user
  host       = mysql_user.prod_user.host
  database   = azurerm_mysql_flexible_database.prod.name
  privileges = [ "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "INDEX", "REFERENCES", "SHOW VIEW"]
}

# Grant read permissions to staging user
resource "mysql_grant" "stage_grant" {
  user       = mysql_user.stage_user.user
  host       = mysql_user.stage_user.host
  database   = azurerm_mysql_flexible_database.stage.name
  privileges = [ "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "INDEX", "REFERENCES", "SHOW VIEW"]
}


resource "azurerm_linux_function_app" "function_app" {
  name                       = local.service_name
  resource_group_name        = data.azurerm_resource_group.existing.name
  location                   = data.azurerm_resource_group.existing.location
  service_plan_id            = data.azurerm_service_plan.existing.id
  storage_account_name       = data.azurerm_storage_account.existing.name
  storage_account_access_key = data.azurerm_storage_account.existing.primary_access_key

  site_config {
    always_on        = true
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key               = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version = "3.12"
    }
  }


  app_settings = {
    "AzureWebJobs.process_iz_no_row_tray_report.Disabled"  = "false"
    "AzureWebJobs.process_scf_no_row_tray_report.Disabled" = "false"
    "AzureWebJobs.process_scf_duplicates_report.Disabled"  = "false"
    "WEBSITE_RUN_FROM_PACKAGE"     = "1"
    "SQLALCHEMY_CONNECTION_STRING" = "mysql+pymysql://${mysql_user.prod_user.user}:${random_password.prod_db_password.result}@${data.azurerm_mysql_flexible_server.existing.fqdn}:3306/${azurerm_mysql_flexible_database.prod.name}"
    "FETCH_ITEM_QUEUE"             = local.storage_queues["fetch-queue"]
    "UPDATE_QUEUE"                 = local.storage_queues["update-queue"]
    "NOTIFICATION_QUEUE"           = local.storage_queues["notification-queue"]
    "UPDATED_ITEMS_CONTAINER"      = local.storage_containers["updated-items-container"]
    "REPORTS_CONTAINER"            = local.storage_containers["reports-container"]
    "SCF_NO_ROW_TRAY_STAGE_TABLE"  = local.storage_tables["scfnorowtraystagetable"]
    "SCF_NO_ROW_TRAY_REPORT_TABLE" = local.storage_tables["scfnorowtrayreporttable"]
    "IZ_NO_ROW_TRAY_STAGE_TABLE"   = local.storage_tables["iznorowtraystagetable"]
    "IZ_NO_ROW_TRAY_NCRON"         = "0 45 23 * * 0-4"
    "SCF_NO_ROW_TRAY_REPORT_NCRON" = "0 30 23 * * 0-4"
    "SCF_DUPLICATES_REPORT_NCRON"  = "0 0 9 * * 1-5"
  }

  sticky_settings {
    app_setting_names = [
      "AzureWebJobs.process_iz_no_row_tray_report.Disabled",
      "AzureWebJobs.process_scf_no_row_tray_report.Disabled",
      "AzureWebJobs.process_scf_duplicates_report.Disabled",
      "SQLALCHEMY_CONNECTION_STRING",
      "FETCH_ITEM_QUEUE",
      "UPDATE_QUEUE",
      "NOTIFICATION_QUEUE",
      "UPDATED_ITEMS_CONTAINER",
      "REPORTS_CONTAINER",
      "SCF_NO_ROW_TRAY_STAGE_TABLE",
      "SCF_NO_ROW_TRAY_REPORT_TABLE",
      "IZ_NO_ROW_TRAY_STAGE_TABLE",
      "IZ_NO_ROW_TRAY_NCRON",
      "SCF_NO_ROW_TRAY_REPORT_NCRON",
      "SCF_DUPLICATES_REPORT_NCRON"
    ]
  }
}

resource "azurerm_linux_function_app_slot" "staging_slot" {
  name                       = "stage"
  function_app_id            = azurerm_linux_function_app.function_app.id
  storage_account_name       = data.azurerm_storage_account.existing.name
  storage_account_access_key = data.azurerm_storage_account.existing.primary_access_key

  site_config {
    always_on                              = true
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key               = azurerm_application_insights.main.instrumentation_key
    application_stack {
      python_version                       = "3.12"
    }
  }

  app_settings = {
    "AzureWebJobs.process_iz_no_row_tray_report.Disabled"  = "true"
    "AzureWebJobs.process_scf_no_row_tray_report.Disabled" = "true"
    "AzureWebJobs.process_scf_duplicates_report.Disabled"  = "true"
    "WEBSITE_RUN_FROM_PACKAGE"     = "1"
    "SQLALCHEMY_CONNECTION_STRING" = "mysql+pymysql://${mysql_user.stage_user.user}:${random_password.stage_db_password.result}@${data.azurerm_mysql_flexible_server.existing.fqdn}:3306/${azurerm_mysql_flexible_database.stage.name}"
    "FETCH_ITEM_QUEUE"             = local.storage_queues["fetch-queue-stage"]
    "UPDATE_QUEUE"                 = local.storage_queues["update-queue-stage"]
    "NOTIFICATION_QUEUE"           = local.storage_queues["notification-queue-stage"]
    "UPDATED_ITEMS_CONTAINER"      = local.storage_containers["updated-items-container-stage"]
    "REPORTS_CONTAINER"            = local.storage_containers["reports-container-stage"]
    "SCF_NO_ROW_TRAY_STAGE_TABLE"  = local.storage_tables["scfnorowtraystagetablestage"]
    "SCF_NO_ROW_TRAY_REPORT_TABLE" = local.storage_tables["scfnorowtrayreporttablestage"]
    "IZ_NO_ROW_TRAY_STAGE_TABLE"   = local.storage_tables["iznorowtraystagetablestage"]
    "IZ_NO_ROW_TRAY_NCRON"         = "0 45 23 1 1 *"
    "SCF_NO_ROW_TRAY_REPORT_NCRON" = "0 30 23 1 1 *"
    "SCF_DUPLICATES_REPORT_NCRON"  = "0 0 9 1 1 *"
  }
}
