'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Label } from './ui/label'
import { Input } from './ui/input'
import { Switch } from './ui/switch'
import { Clock } from 'lucide-react'

interface DaySchedule {
  enabled: boolean
  start: string
  end: string
}

interface WeekSchedule {
  monday: DaySchedule
  tuesday: DaySchedule
  wednesday: DaySchedule
  thursday: DaySchedule
  friday: DaySchedule
  saturday: DaySchedule
  sunday: DaySchedule
}

interface AgentScheduleEditorProps {
  value: WeekSchedule
  onChange: (schedule: WeekSchedule) => void
}

const DEFAULT_SCHEDULE: WeekSchedule = {
  monday: { enabled: true, start: '09:00', end: '17:00' },
  tuesday: { enabled: true, start: '09:00', end: '17:00' },
  wednesday: { enabled: true, start: '09:00', end: '17:00' },
  thursday: { enabled: true, start: '09:00', end: '17:00' },
  friday: { enabled: true, start: '09:00', end: '17:00' },
  saturday: { enabled: false, start: '09:00', end: '17:00' },
  sunday: { enabled: false, start: '09:00', end: '17:00' },
}

export function AgentScheduleEditor({ value = DEFAULT_SCHEDULE, onChange }: AgentScheduleEditorProps) {
  const days = [
    { key: 'monday' as keyof WeekSchedule, label: 'Monday' },
    { key: 'tuesday' as keyof WeekSchedule, label: 'Tuesday' },
    { key: 'wednesday' as keyof WeekSchedule, label: 'Wednesday' },
    { key: 'thursday' as keyof WeekSchedule, label: 'Thursday' },
    { key: 'friday' as keyof WeekSchedule, label: 'Friday' },
    { key: 'saturday' as keyof WeekSchedule, label: 'Saturday' },
    { key: 'sunday' as keyof WeekSchedule, label: 'Sunday' },
  ]

  const updateDay = (day: keyof WeekSchedule, updates: Partial<DaySchedule>) => {
    onChange({
      ...value,
      [day]: { ...value[day], ...updates },
    })
  }

  const applyToAll = (template: DaySchedule) => {
    const newSchedule = { ...value }
    days.forEach(({ key }) => {
      newSchedule[key] = { ...template }
    })
    onChange(newSchedule)
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          <CardTitle>Active Hours</CardTitle>
        </div>
        <CardDescription>
          Set when this agent should process emails. Agent will only run during active hours in your timezone.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => applyToAll({ enabled: true, start: '09:00', end: '17:00' })}
            className="rounded-md border px-3 py-1 text-sm hover:bg-accent"
          >
            9-5 Weekdays
          </button>
          <button
            type="button"
            onClick={() => applyToAll({ enabled: true, start: '00:00', end: '23:59' })}
            className="rounded-md border px-3 py-1 text-sm hover:bg-accent"
          >
            24/7
          </button>
          <button
            type="button"
            onClick={() => applyToAll({ enabled: false, start: '09:00', end: '17:00' })}
            className="rounded-md border px-3 py-1 text-sm hover:bg-accent"
          >
            Disable All
          </button>
        </div>

        {/* Day by Day Schedule */}
        <div className="space-y-3">
          {days.map(({ key, label }) => {
            const daySchedule = value[key]
            return (
              <div key={key} className="flex items-center gap-4">
                <div className="flex w-32 items-center gap-2">
                  <Switch
                    checked={daySchedule.enabled}
                    onCheckedChange={(enabled) => updateDay(key, { enabled })}
                  />
                  <Label className="text-sm font-medium">{label}</Label>
                </div>

                {daySchedule.enabled ? (
                  <div className="flex flex-1 items-center gap-2">
                    <Input
                      type="time"
                      value={daySchedule.start}
                      onChange={(e) => updateDay(key, { start: e.target.value })}
                      className="w-32"
                    />
                    <span className="text-muted-foreground">to</span>
                    <Input
                      type="time"
                      value={daySchedule.end}
                      onChange={(e) => updateDay(key, { end: e.target.value })}
                      className="w-32"
                    />
                  </div>
                ) : (
                  <span className="text-sm text-muted-foreground">Inactive</span>
                )}
              </div>
            )
          })}
        </div>

        {/* Schedule Summary */}
        <div className="rounded-md bg-muted p-3 text-sm">
          <strong>Summary:</strong>{' '}
          {days.filter(({ key }) => value[key].enabled).length === 0 && 'Agent is inactive all week'}
          {days.filter(({ key }) => value[key].enabled).length === 7 &&
            value.monday.start === '00:00' &&
            value.monday.end === '23:59' &&
            'Agent runs 24/7'}
          {days.filter(({ key }) => value[key].enabled).length > 0 &&
            days.filter(({ key }) => value[key].enabled).length < 7 &&
            `Active ${days.filter(({ key }) => value[key].enabled).length} days per week`}
        </div>
      </CardContent>
    </Card>
  )
}

// Helper to check if agent should run now
export function isAgentActive(schedule: WeekSchedule, timezone: string = 'UTC'): boolean {
  const now = new Date()
  const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
  const currentDay = dayNames[now.getDay()] as keyof WeekSchedule

  const daySchedule = schedule[currentDay]

  if (!daySchedule?.enabled) return false

  const currentTime = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    timeZone: timezone
  })

  return currentTime >= daySchedule.start && currentTime <= daySchedule.end
}
