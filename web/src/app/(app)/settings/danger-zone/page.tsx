'use client'

import { useState } from 'react'
import { signOut } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertTriangle, Trash2 } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/components/ui/use-toast'

export default function DangerZonePage() {
  const { toast } = useToast()
  const [password, setPassword] = useState('')
  const [deleteText, setDeleteText] = useState('')
  const [loading, setLoading] = useState(false)

  const handleDeleteAccount = async () => {
    if (deleteText !== 'DELETE MY ACCOUNT') {
      toast({
        title: 'Confirmation required',
        description: 'Please type "DELETE MY ACCOUNT" to confirm',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      const res = await fetch('/api/user/delete-account', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })

      const data = await res.json()

      if (res.ok) {
        toast({
          title: 'Account deletion scheduled',
          description: 'Your account will be deleted in 30 days. Check your email for reactivation instructions.',
        })

        // Sign out after deletion
        setTimeout(() => signOut({ callbackUrl: '/' }), 2000)
      } else {
        toast({
          title: 'Deletion failed',
          description: data.error || 'Failed to delete account',
          variant: 'destructive',
        })
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Something went wrong. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container max-w-2xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-red-600">Danger Zone</h1>
        <p className="text-muted-foreground">Irreversible and destructive actions</p>
      </div>

      <Card className="border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <CardTitle className="text-red-600">Delete Account</CardTitle>
          </div>
          <CardDescription>
            Permanently delete your account and all associated data
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md bg-white p-4 dark:bg-gray-900">
            <h4 className="mb-2 font-semibold">What will happen:</h4>
            <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
              <li>All your agents will be permanently disabled</li>
              <li>All email data and history will be deleted</li>
              <li>All analytics and reports will be removed</li>
              <li>You will have 30 days to cancel this action</li>
              <li>After 30 days, all data will be permanently erased</li>
            </ul>
          </div>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="w-full">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete My Account
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be easily undone. Your account will be scheduled for deletion
                  in 30 days.
                </AlertDialogDescription>
              </AlertDialogHeader>

              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Confirm with your password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="deleteConfirm">
                    Type <strong>DELETE MY ACCOUNT</strong> to confirm
                  </Label>
                  <Input
                    id="deleteConfirm"
                    value={deleteText}
                    onChange={(e) => setDeleteText(e.target.value)}
                    placeholder="DELETE MY ACCOUNT"
                  />
                </div>
              </div>

              <AlertDialogFooter>
                <AlertDialogCancel onClick={() => {
                  setPassword('')
                  setDeleteText('')
                }}>
                  Cancel
                </AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDeleteAccount}
                  disabled={loading || deleteText !== 'DELETE MY ACCOUNT' || !password}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {loading ? 'Deleting...' : 'Delete Account'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  )
}
