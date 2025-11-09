'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'

export default function ReactivateAccountPage({ params }: { params: { token: string } }) {
  const router = useRouter()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetch('/api/user/reactivate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: params.token }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setStatus('success')
          setMessage('Your account has been reactivated!')
          setTimeout(() => router.push('/auth/signin'), 3000)
        } else {
          setStatus('error')
          setMessage(data.error || 'Reactivation failed')
        }
      })
      .catch(() => {
        setStatus('error')
        setMessage('Something went wrong')
      })
  }, [params.token, router])

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === 'loading' && <Loader2 className="h-16 w-16 animate-spin text-primary" />}
            {status === 'success' && <CheckCircle2 className="h-16 w-16 text-green-600" />}
            {status === 'error' && <XCircle className="h-16 w-16 text-red-600" />}
          </div>
          <CardTitle>
            {status === 'loading' && 'Reactivating...'}
            {status === 'success' && 'Welcome Back!'}
            {status === 'error' && 'Reactivation Failed'}
          </CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent>
          {status === 'success' && (
            <p className="text-center text-sm text-muted-foreground">
              Redirecting to sign in...
            </p>
          )}
          {status === 'error' && (
            <Button onClick={() => router.push('/auth/signin')} className="w-full">
              Go to Sign In
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
