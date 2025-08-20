# Corresponds to secrets.TF_STATE_RG
resource_group_name  = "rg-alma-item-checks-tfstate"

# Corresponds to secrets.TF_STATE_SA
storage_account_name = "stterraformstatewrlc123"

# These are static in your workflow
container_name       = "tfstate"
key                  = "aicwebhookserviceterraform.tfstate"
