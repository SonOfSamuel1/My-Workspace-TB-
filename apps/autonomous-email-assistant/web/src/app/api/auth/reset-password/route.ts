import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { hash } from 'bcryptjs'
import { z } from 'zod'
import { validatePassword } from '@/components/password-strength'

const resetPasswordSchema = z.object({
  token: z.string().min(1),
  password: z.string().min(8),
})

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { token, password } = resetPasswordSchema.parse(body)

    // Validate password strength
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.valid) {
      return NextResponse.json(
        { error: 'Password does not meet requirements', details: passwordValidation.errors },
        { status: 400 }
      )
    }

    // Find the reset token
    const resetToken = await prisma.verificationToken.findFirst({
      where: {
        token,
        identifier: {
          startsWith: 'reset-',
        },
      },
    })

    if (!resetToken) {
      return NextResponse.json(
        { error: 'Invalid or expired reset link' },
        { status: 400 }
      )
    }

    // Check if token is expired
    if (resetToken.expires < new Date()) {
      await prisma.verificationToken.delete({
        where: {
          identifier_token: {
            identifier: resetToken.identifier,
            token: resetToken.token,
          },
        },
      })
      return NextResponse.json(
        { error: 'Reset link has expired' },
        { status: 400 }
      )
    }

    // Extract email from identifier (remove 'reset-' prefix)
    const email = resetToken.identifier.replace('reset-', '')

    // Find user
    const user = await prisma.user.findUnique({
      where: { email },
    })

    if (!user) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      )
    }

    // Hash new password
    const hashedPassword = await hash(password, 12)

    // Update user password
    await prisma.user.update({
      where: { email },
      data: { password: hashedPassword },
    })

    // Delete the used token
    await prisma.verificationToken.delete({
      where: {
        identifier_token: {
          identifier: resetToken.identifier,
          token: resetToken.token,
        },
      },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request' },
        { status: 400 }
      )
    }

    console.error('Reset password error:', error)
    return NextResponse.json(
      { error: 'Failed to reset password' },
      { status: 500 }
    )
  }
}
