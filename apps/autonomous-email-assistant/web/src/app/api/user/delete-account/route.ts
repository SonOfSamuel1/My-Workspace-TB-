import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { compare } from 'bcryptjs'
import { sendAccountDeletionEmail } from '@/lib/email-service'
import crypto from 'crypto'
import { z } from 'zod'

const deleteAccountSchema = z.object({
  password: z.string().min(1),
})

export async function DELETE(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions)

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const { password } = deleteAccountSchema.parse(body)

    // Get user with password
    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
    })

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }

    // Verify password
    if (user.password) {
      const isValid = await compare(password, user.password)
      if (!isValid) {
        return NextResponse.json({ error: 'Invalid password' }, { status: 401 })
      }
    }

    // Generate reactivation token
    const reactivationToken = crypto.randomBytes(32).toString('hex')
    const expires = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) // 30 days

    // Store reactivation token
    await prisma.verificationToken.create({
      data: {
        identifier: `reactivate-${user.email}`,
        token: reactivationToken,
        expires,
      },
    })

    // Soft delete user and disable all agents
    await prisma.$transaction([
      prisma.user.update({
        where: { id: session.user.id },
        data: { deletedAt: new Date() },
      }),
      prisma.agent.updateMany({
        where: { userId: session.user.id },
        data: { enabled: false, deletedAt: new Date() },
      }),
    ])

    // Send deletion confirmation email
    await sendAccountDeletionEmail(user.email, reactivationToken)

    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request' }, { status: 400 })
    }

    console.error('Delete account error:', error)
    return NextResponse.json(
      { error: 'Failed to delete account' },
      { status: 500 }
    )
  }
}
