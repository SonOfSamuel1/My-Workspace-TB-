'use client'

import * as React from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export function ThemeToggle() {
  const { setTheme } = useTheme()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// Radio group version for settings page
export function ThemeSelector() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null // Avoid hydration mismatch
  }

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Theme</label>
      <div className="flex gap-3">
        <button
          onClick={() => setTheme('light')}
          className={`flex-1 rounded-lg border-2 p-4 transition-colors ${
            theme === 'light'
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50'
          }`}
        >
          <Sun className="mx-auto mb-2 h-6 w-6" />
          <p className="text-sm font-medium">Light</p>
        </button>
        <button
          onClick={() => setTheme('dark')}
          className={`flex-1 rounded-lg border-2 p-4 transition-colors ${
            theme === 'dark'
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50'
          }`}
        >
          <Moon className="mx-auto mb-2 h-6 w-6" />
          <p className="text-sm font-medium">Dark</p>
        </button>
        <button
          onClick={() => setTheme('system')}
          className={`flex-1 rounded-lg border-2 p-4 transition-colors ${
            theme === 'system'
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50'
          }`}
        >
          <div className="mx-auto mb-2 flex h-6 w-6 items-center justify-center">
            <Sun className="h-3 w-3" />
            <Moon className="h-3 w-3" />
          </div>
          <p className="text-sm font-medium">System</p>
        </button>
      </div>
    </div>
  )
}
