'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Upload, User } from 'lucide-react'
import { trpc } from '@/lib/trpc/client'
import { useToast } from '@/components/ui/use-toast'

export default function ProfilePage() {
  const { data: session, update: updateSession } = useSession()
  const { toast } = useToast()
  const [name, setName] = useState(session?.user?.name || '')
  const [email, setEmail] = useState(session?.user?.email || '')
  const [timezone, setTimezone] = useState('America/New_York')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)

  const updateProfile = trpc.user.updateProfile.useMutation({
    onSuccess: async () => {
      toast({ title: 'Profile updated successfully' })
      await updateSession()
    },
    onError: (error) => {
      toast({ title: 'Failed to update profile', description: error.message, variant: 'destructive' })
    },
  })

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setAvatarFile(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    let avatarUrl = session?.user?.image

    // Upload avatar if changed
    if (avatarFile) {
      const formData = new FormData()
      formData.append('avatar', avatarFile)

      const uploadRes = await fetch('/api/upload/avatar', {
        method: 'POST',
        body: formData,
      })

      if (uploadRes.ok) {
        const data = await uploadRes.json()
        avatarUrl = data.url
      }
    }

    updateProfile.mutate({
      name,
      email,
      timezone,
      image: avatarUrl,
    })
  }

  const timezones = [
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Phoenix',
    'Europe/London',
    'Europe/Paris',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Australia/Sydney',
  ]

  return (
    <div className="container max-w-2xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Profile Settings</h1>
        <p className="text-muted-foreground">Manage your account information and preferences</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
            <CardDescription>Update your personal details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Avatar Upload */}
            <div className="flex items-center gap-4">
              <Avatar className="h-20 w-20">
                <AvatarImage src={avatarPreview || session?.user?.image || undefined} />
                <AvatarFallback>
                  <User className="h-10 w-10" />
                </AvatarFallback>
              </Avatar>
              <div>
                <Label htmlFor="avatar" className="cursor-pointer">
                  <div className="flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 hover:bg-accent hover:text-accent-foreground">
                    <Upload className="h-4 w-4" />
                    <span className="text-sm">Upload Photo</span>
                  </div>
                  <Input
                    id="avatar"
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleAvatarChange}
                  />
                </Label>
                <p className="mt-1 text-xs text-muted-foreground">
                  JPG, PNG or GIF. Max 2MB.
                </p>
              </div>
            </div>

            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
              />
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
              />
              {email !== session?.user?.email && (
                <p className="text-sm text-muted-foreground">
                  Changing your email will require re-verification
                </p>
              )}
            </div>

            {/* Timezone */}
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {timezones.map((tz) => (
                    <SelectItem key={tz} value={tz}>
                      {tz.replace(/_/g, ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => {
            setName(session?.user?.name || '')
            setEmail(session?.user?.email || '')
            setAvatarPreview(null)
            setAvatarFile(null)
          }}>
            Cancel
          </Button>
          <Button type="submit" disabled={updateProfile.isLoading}>
            {updateProfile.isLoading ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </div>
  )
}
