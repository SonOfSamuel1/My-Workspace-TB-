import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

const reactivateSchema = z.object({
  token: z.string().min(1),
})

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { token } = reactivateSchema.parse(body)

    // Find the reactivation token
    const reactivationToken = await prisma.verificationToken.findFirst({
      where: {
        token,
        identifier: {
          startsWith: 'reactivate-',
        },
      },
    })

    if (!reactivationToken) {
      return NextResponse.json(
        { error: 'Invalid or expired reactivation link' },
        { status: 400 }
      )
    }

    // Check if token is expired
    if (reactivationToken.expires < new Date()) {
      await prisma.verificationToken.delete({
        where: {
          identifier_token: {
            identifier: reactivationToken.identifier,
            token: reactivationToken.token,
          },
        },
      })
      return NextResponse.json(
        { error: 'Reactivation link has expired. Your account has been permanently deleted.' },
        { status: 400 }
      )
    }

    // Extract email from identifier
    const email = reactivationToken.identifier.replace('reactivate-', '')

    // Reactivate user and agents
    await prisma.$transaction([
      prisma.user.update({
        where: { email },
        data: { deletedAt: null },
      }),
      prisma.agent.updateMany({
        where: { user: { email } },
        data: { deletedAt: null },
      }),
    ])

    // Delete the used token
    await prisma.verificationToken.delete({
      where: {
        identifier_token: {
          identifier: reactivationToken.identifier,
          token: reactivationToken.token,
        },
      },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request' }, { status: 400 })
    }

    console.error('Reactivate account error:', error)
    return NextResponse.json(
      { error: 'Failed to reactivate account' },
      { status: 500 }
    )
  }
}
