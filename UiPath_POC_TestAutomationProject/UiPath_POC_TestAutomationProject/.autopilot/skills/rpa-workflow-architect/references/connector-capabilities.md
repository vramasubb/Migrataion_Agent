# Discover Connector Capabilities (For IS/Connector Workflows)

When the workflow involves Integration Service connectors (e.g., Salesforce, Jira, ServiceNow), explore the connector's capabilities before writing XAML:

```
# What activities does this connector offer?
RpaActivitySearchTool:
  query: "<connector name> activities"
  tags: "<connector-key>"
  limit: 20

# What data objects/resources does it expose?
GetProjectContextTool:
  queryType: "entities"   → lists available resources, objects, connections
```

## Connection Management

**Check if a connection exists:**
```
GetProjectContextTool:
  queryType: "full"   → see all available connections and their IDs under "connections"
```

**If no connection exists**, you have two options:
1. **Ask the user to create one** — they need to configure the connection in Studio Desktop's Integration Service panel (requires OAuth/credentials)
2. **Use a placeholder** — insert the dynamic activity with an empty `connectionId` and inform the user they need to configure the connection in Studio

**Verify a connection is active:**
```
GetProjectContextTool:
  queryType: "full"   → inspect connection status in the returned context
```

If the context shows a connection is stale or invalid, inform the user to re-authenticate it in Studio Desktop.
