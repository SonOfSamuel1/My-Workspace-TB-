'use client'

import { signIn } from 'next-auth/react'
import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Bot, Mail, Github, Chrome, AlertCircle } from 'lucide-react'
import Link from 'next/link'

export default function SignInPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const callbackUrl = searchParams.get('callbackUrl') || '/dashboard'
  const error = searchParams.get('error')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      })

      if (result?.error) {
        console.error('Sign in error:', result.error)
      } else if (result?.ok) {
        router.push(callbackUrl)
      }
    } catch (error) {
      console.error('Sign in error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleOAuthSignIn = (provider: 'google' | 'github') => {
    signIn(provider, { callbackUrl })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center">
              <Bot className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
          <CardDescription>
            Sign in to your Mail Agent Manager account
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-destructive">
                  {error === 'OAuthAccountNotLinked'
                    ? 'Email already in use with different provider'
                    : error === 'CredentialsSignin'
                    ? 'Invalid email or password'
                    : 'An error occurred. Please try again.'}
                </p>
              </div>
            </div>
          )}

          {/* OAuth Buttons */}
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => handleOAuthSignIn('google')}
            >
              <Chrome className="h-4 w-4 mr-2" />
              Continue with Google
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => handleOAuthSignIn('github')}
            >
              <Github className="h-4 w-4 mr-2" />
              Continue with GitHub
            </Button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or continue with email
              </span>
            </div>
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleEmailSignIn} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="demo@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  href="/auth/forgot-password"
                  className="text-xs text-primary hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Signing in...
                </>
              ) : (
                <>
                  <Mail className="h-4 w-4 mr-2" />
                  Sign in with Email
                </>
              )}
            </Button>
          </form>

          <div className="text-center text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link href="/auth/signup" className="text-primary hover:underline">
              Sign up
            </Link>
          </div>

          {/* Demo credentials hint */}
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs text-blue-900 dark:text-blue-100 font-semibold mb-1">
              Demo Credentials
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-200">
              Email: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">demo@example.com</code>
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-200 mt-1">
              Password: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">demo</code>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
