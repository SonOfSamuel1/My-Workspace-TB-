'use client'

import { useMemo } from 'react'
import { Check, X } from 'lucide-react'

interface PasswordStrengthProps {
  password: string
  showRequirements?: boolean
}

interface Requirement {
  label: string
  test: (password: string) => boolean
}

const requirements: Requirement[] = [
  { label: 'At least 8 characters', test: (p) => p.length >= 8 },
  { label: 'Contains uppercase letter', test: (p) => /[A-Z]/.test(p) },
  { label: 'Contains lowercase letter', test: (p) => /[a-z]/.test(p) },
  { label: 'Contains number', test: (p) => /\d/.test(p) },
  { label: 'Contains special character', test: (p) => /[!@#$%^&*(),.?":{}|<>]/.test(p) },
]

export function PasswordStrength({ password, showRequirements = true }: PasswordStrengthProps) {
  const strength = useMemo(() => {
    if (!password) return { score: 0, label: '', color: '' }

    const passed = requirements.filter((req) => req.test(password)).length
    const score = (passed / requirements.length) * 100

    if (score < 40) return { score, label: 'Weak', color: 'bg-red-500' }
    if (score < 80) return { score, label: 'Medium', color: 'bg-yellow-500' }
    return { score, label: 'Strong', color: 'bg-green-500' }
  }, [password])

  if (!password) return null

  return (
    <div className="space-y-2">
      {/* Strength Meter */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Password strength:</span>
          <span className={`font-medium ${
            strength.label === 'Weak' ? 'text-red-600' :
            strength.label === 'Medium' ? 'text-yellow-600' :
            'text-green-600'
          }`}>
            {strength.label}
          </span>
        </div>
        <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${strength.color} transition-all duration-300`}
            style={{ width: `${strength.score}%` }}
          />
        </div>
      </div>

      {/* Requirements Checklist */}
      {showRequirements && (
        <ul className="space-y-1 text-sm">
          {requirements.map((req, index) => {
            const passed = req.test(password)
            return (
              <li
                key={index}
                className={`flex items-center gap-2 ${
                  passed ? 'text-green-600' : 'text-muted-foreground'
                }`}
              >
                {passed ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <X className="h-4 w-4" />
                )}
                {req.label}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

// Validation helper
export function validatePassword(password: string): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  requirements.forEach((req) => {
    if (!req.test(password)) {
      errors.push(req.label)
    }
  })

  return {
    valid: errors.length === 0,
    errors,
  }
}
