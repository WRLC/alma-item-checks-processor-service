variable "service_name" {
  type = string
}

variable "shared_project_resource_group_name" {
  type = string
}

variable "shared_storage_account_name" {
  type = string
}

variable "asp_resource_group_name" {
  type = string
}

variable "app_service_plan_name" {
  type = string
}

variable "log_analytics_workspace_name" {
  type = string
}

variable "law_resource_group_name" {
  type = string
}

variable "mysql_server_name" {
  type        = string
  description = "Name of the existing Azure MySQL Flexible Server"
}

variable "mysql_server_resource_group_name" {
  type        = string
  description = "Resource group name where the MySQL Flexible Server is located"
}


variable "mysql_admin_username" {
  type        = string
  description = "MySQL server administrator username"
}

variable "mysql_admin_password" {
  type        = string
  description = "MySQL server administrator password"
  sensitive   = true
}
