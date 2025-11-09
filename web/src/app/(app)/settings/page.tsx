'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { trpc } from '@/lib/trpc/client'
import {
  Settings as SettingsIcon,
  User,
  Bell,
  Download,
  Upload,
  Key,
  Palette,
  Copy,
  Check,
} from 'lucide-react'

export default function SettingsPage() {
  const [copied, setCopied] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)

  const { data: agents } = trpc.agent.list.useQuery()

  const copyApiKey = () => {
    navigator.clipboard.writeText(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExport = async () => {
    if (!agents) return

    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      agents: agents.map(agent => ({
        name: agent.name,
        agentEmail: agent.agentEmail,
        description: agent.description,
        config: agent.config,
      })),
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mail-agents-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleImport = async () => {
    if (!importFile) return

    try {
      const text = await importFile.text()
      const data = JSON.parse(text)

      // Validate structure
      if (!data.agents || !Array.isArray(data.agents)) {
        alert('Invalid import file format')
        return
      }

      // TODO: Implement bulk import via tRPC
      alert(`Found ${data.agents.length} agents to import. Import functionality coming soon!`)
    } catch (error) {
      alert('Failed to parse import file')
    }
  }

  return (
    <div className="container mx-auto p-4 sm:p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account and preferences
        </p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5">
          <TabsTrigger value="profile">
            <User className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Profile</span>
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Notifications</span>
          </TabsTrigger>
          <TabsTrigger value="appearance">
            <Palette className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Appearance</span>
          </TabsTrigger>
          <TabsTrigger value="api">
            <Key className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">API Keys</span>
          </TabsTrigger>
          <TabsTrigger value="export">
            <Download className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Export/Import</span>
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Update your account details and preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="h-20 w-20 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold">
                  U
                </div>
                <div>
                  <Button variant="outline" size="sm">
                    Change Avatar
                  </Button>
                </div>
              </div>

              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input id="firstName" placeholder="John" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input id="lastName" placeholder="Doe" />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="user@example.com" />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Input id="timezone" value="America/New_York" disabled />
                </div>
              </div>

              <Button>Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you want to be notified
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Email Notifications</h4>
                    <p className="text-sm text-muted-foreground">
                      Receive email summaries of agent activity
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Tier 1 Escalations</h4>
                    <p className="text-sm text-muted-foreground">
                      Instant notifications for urgent emails
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Approval Requests</h4>
                    <p className="text-sm text-muted-foreground">
                      Notify when drafts need review
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Browser Notifications</h4>
                    <p className="text-sm text-muted-foreground">
                      Show desktop notifications when app is open
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">SMS Alerts</h4>
                    <p className="text-sm text-muted-foreground">
                      Send SMS for critical escalations
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" />
                </div>
              </div>

              <Button>Save Preferences</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance">
          <Card>
            <CardHeader>
              <CardTitle>Appearance Settings</CardTitle>
              <CardDescription>
                Customize how the app looks
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <Label>Theme</Label>
                  <div className="grid grid-cols-3 gap-4 mt-2">
                    <button className="border-2 border-primary rounded-lg p-4 hover:bg-accent transition-colors">
                      <div className="mb-2 text-sm font-medium">Light</div>
                      <div className="h-16 bg-white border rounded" />
                    </button>
                    <button className="border-2 rounded-lg p-4 hover:bg-accent transition-colors">
                      <div className="mb-2 text-sm font-medium">Dark</div>
                      <div className="h-16 bg-gray-900 border rounded" />
                    </button>
                    <button className="border-2 rounded-lg p-4 hover:bg-accent transition-colors">
                      <div className="mb-2 text-sm font-medium">System</div>
                      <div className="h-16 bg-gradient-to-r from-white to-gray-900 border rounded" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Compact Mode</h4>
                    <p className="text-sm text-muted-foreground">
                      Reduce spacing for denser layout
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Show Tier Colors</h4>
                    <p className="text-sm text-muted-foreground">
                      Use color-coded badges for email tiers
                    </p>
                  </div>
                  <input type="checkbox" className="toggle" defaultChecked />
                </div>
              </div>

              <Button>Save Settings</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api">
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
              <CardDescription>
                Manage API keys for integration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div>
                  <Label>Integration API Key</Label>
                  <div className="flex gap-2 mt-2">
                    <Input
                      type="password"
                      value="sk-proj-••••••••••••••••"
                      disabled
                      className="font-mono"
                    />
                    <Button
                      variant="outline"
                      onClick={copyApiKey}
                      size="icon"
                    >
                      {copied ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for CLI integration. Store securely.
                  </p>
                </div>

                <div>
                  <Label>Web App URL</Label>
                  <div className="flex gap-2 mt-2">
                    <Input
                      value={process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}
                      disabled
                      className="font-mono text-sm"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Your web app deployment URL for API calls
                  </p>
                </div>
              </div>

              <div className="p-4 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg">
                <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-2">
                  Security Best Practices
                </h4>
                <ul className="text-sm text-amber-800 dark:text-amber-200 space-y-1 list-disc list-inside">
                  <li>Never share your API keys publicly</li>
                  <li>Rotate keys regularly (every 90 days)</li>
                  <li>Use environment variables in production</li>
                  <li>Monitor API usage for suspicious activity</li>
                </ul>
              </div>

              <div className="flex gap-2">
                <Button variant="outline">Rotate API Key</Button>
                <Button variant="destructive">Revoke All Keys</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Export/Import Tab */}
        <TabsContent value="export">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Export */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="h-5 w-5" />
                  Export Configuration
                </CardTitle>
                <CardDescription>
                  Download all agent configurations as JSON
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Export includes:
                  </p>
                  <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
                    <li>Agent names and emails</li>
                    <li>Configuration settings</li>
                    <li>Off-limits contacts</li>
                    <li>Business hours & timezone</li>
                  </ul>
                </div>

                <div className="p-3 bg-muted rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">
                      {agents?.length || 0} agents ready to export
                    </span>
                    <Badge variant="outline">
                      {new Date().toLocaleDateString()}
                    </Badge>
                  </div>
                </div>

                <Button onClick={handleExport} className="w-full" disabled={!agents || agents.length === 0}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Agents
                </Button>
              </CardContent>
            </Card>

            {/* Import */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Import Configuration
                </CardTitle>
                <CardDescription>
                  Restore agents from a backup file
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="import-file">Select backup file</Label>
                  <Input
                    id="import-file"
                    type="file"
                    accept=".json"
                    onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Only JSON files exported from this app are supported
                  </p>
                </div>

                {importFile && (
                  <div className="p-3 bg-muted rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">
                        {importFile.name}
                      </span>
                      <Badge variant="outline">
                        {(importFile.size / 1024).toFixed(1)} KB
                      </Badge>
                    </div>
                  </div>
                )}

                <div className="p-3 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <p className="text-xs text-amber-800 dark:text-amber-200">
                    <strong>Warning:</strong> Importing will create new agents. Existing agents with the same email will not be modified.
                  </p>
                </div>

                <Button
                  onClick={handleImport}
                  variant="outline"
                  className="w-full"
                  disabled={!importFile}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Import Agents
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
