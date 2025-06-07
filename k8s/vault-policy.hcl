# Vault policy for sales-discovery-bot
path "kv/data/agents/insta-agents/sales-discovery-bot/*" {
  capabilities = ["read"]
}

path "kv/metadata/agents/insta-agents/sales-discovery-bot/*" {
  capabilities = ["read", "list"]
}