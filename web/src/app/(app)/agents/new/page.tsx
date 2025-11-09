'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { trpc } from '@/lib/trpc/client'
import { ArrowLeft, Plus, X } from 'lucide-react'
import Link from 'next/link'

const TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Phoenix',
  'America/Anchorage',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Asia/Tokyo',
  'Australia/Sydney',
]

export default function NewAgentPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [agentEmail, setAgentEmail] = useState('')
  const [description, setDescription] = useState('')
  const [timezone, setTimezone] = useState('America/New_York')
  const [businessHoursStart, setBusinessHoursStart] = useState(9)
  const [businessHoursEnd, setBusinessHoursEnd] = useState(17)
  const [communicationStyle, setCommunicationStyle] = useState('professional')
  const [offLimitsContacts, setOffLimitsContacts] = useState<string[]>([])
  const [newContact, setNewContact] = useState('')

  const createAgent = trpc.agent.create.useMutation({
    onSuccess: (data) => {
      router.push(`/agents/${data.id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    createAgent.mutate({
      name,
      agentEmail,
      description,
      config: {
        timezone,
        businessHours: {
          start: businessHoursStart,
          end: businessHoursEnd,
        },
        offLimitsContacts,
        communicationStyle,
      },
    })
  }

  const addOffLimitsContact = () => {
    if (newContact && !offLimitsContacts.includes(newContact)) {
      setOffLimitsContacts([...offLimitsContacts, newContact])
      setNewContact('')
    }
  }

  const removeOffLimitsContact = (email: string) => {
    setOffLimitsContacts(offLimitsContacts.filter((c) => c !== email))
  }

  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <div className="mb-6">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create New Email Agent</CardTitle>
          <CardDescription>
            Set up a new autonomous email agent to manage your inbox
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Basic Information</h3>

              <div className="space-y-2">
                <Label htmlFor="name">Agent Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Executive Assistant"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  A friendly name to identify this agent
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="agentEmail">Agent Email Address *</Label>
                <Input
                  id="agentEmail"
                  type="email"
                  value={agentEmail}
                  onChange={(e) => setAgentEmail(e.target.value)}
                  placeholder="assistant@yourdomain.com"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  The email address this agent will monitor
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the purpose of this agent..."
                  rows={3}
                />
              </div>
            </div>

            {/* Schedule Configuration */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Schedule Configuration</h3>

              <div className="space-y-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Select value={timezone} onValueChange={setTimezone}>
                  <SelectTrigger id="timezone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEZONES.map((tz) => (
                      <SelectItem key={tz} value={tz}>
                        {tz}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="startHour">Business Hours Start</Label>
                  <Select
                    value={businessHoursStart.toString()}
                    onValueChange={(v) => setBusinessHoursStart(parseInt(v))}
                  >
                    <SelectTrigger id="startHour">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 24 }, (_, i) => (
                        <SelectItem key={i} value={i.toString()}>
                          {i.toString().padStart(2, '0')}:00
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="endHour">Business Hours End</Label>
                  <Select
                    value={businessHoursEnd.toString()}
                    onValueChange={(v) => setBusinessHoursEnd(parseInt(v))}
                  >
                    <SelectTrigger id="endHour">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 24 }, (_, i) => (
                        <SelectItem key={i} value={i.toString()}>
                          {i.toString().padStart(2, '0')}:00
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Communication Style */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Communication Style</h3>

              <div className="space-y-2">
                <Label htmlFor="style">Response Style</Label>
                <Select value={communicationStyle} onValueChange={setCommunicationStyle}>
                  <SelectTrigger id="style">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="friendly">Friendly</SelectItem>
                    <SelectItem value="formal">Formal</SelectItem>
                    <SelectItem value="concise">Concise</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  How the agent should communicate in responses
                </p>
              </div>
            </div>

            {/* Off-Limits Contacts */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Off-Limits Contacts</h3>
              <p className="text-sm text-muted-foreground">
                Emails from these contacts will always be escalated (Tier 1) regardless of content
              </p>

              <div className="flex gap-2">
                <Input
                  value={newContact}
                  onChange={(e) => setNewContact(e.target.value)}
                  placeholder="email@example.com"
                  type="email"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addOffLimitsContact()
                    }
                  }}
                />
                <Button
                  type="button"
                  onClick={addOffLimitsContact}
                  variant="outline"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>

              {offLimitsContacts.length > 0 && (
                <div className="space-y-2">
                  {offLimitsContacts.map((contact) => (
                    <div
                      key={contact}
                      className="flex items-center justify-between p-2 bg-muted rounded-md"
                    >
                      <span className="text-sm">{contact}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeOffLimitsContact(contact)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Submit */}
            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={createAgent.isPending}
                className="flex-1"
              >
                {createAgent.isPending ? 'Creating...' : 'Create Agent'}
              </Button>
              <Link href="/dashboard" className="flex-1">
                <Button type="button" variant="outline" className="w-full">
                  Cancel
                </Button>
              </Link>
            </div>

            {createAgent.error && (
              <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
                {createAgent.error.message}
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
