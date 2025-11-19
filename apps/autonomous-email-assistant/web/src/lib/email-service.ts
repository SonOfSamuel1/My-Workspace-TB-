import { Resend } from 'resend'
import crypto from 'crypto'
import { prisma } from './prisma'
import { logger } from './logger'

const resend = new Resend(process.env.RESEND_API_KEY)

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
const FROM_EMAIL = process.env.FROM_EMAIL || 'noreply@yourdomain.com'

// Email Verification (Item 1)
export async function sendVerificationEmail(email: string, userId: string) {
  const token = crypto.randomBytes(32).toString('hex')
  const expires = new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours

  await prisma.verificationToken.create({
    data: {
      identifier: email,
      token,
      expires,
    },
  })

  const verificationUrl = `${APP_URL}/auth/verify?token=${token}`

  try {
    await resend.emails.send({
      from: FROM_EMAIL,
      to: email,
      subject: 'Verify your email address',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .button {
                display: inline-block;
                padding: 12px 24px;
                background: #0070f3;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 20px 0;
              }
              .footer { margin-top: 40px; font-size: 12px; color: #666; }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>Verify Your Email</h1>
              <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
              <a href="${verificationUrl}" class="button">Verify Email Address</a>
              <p>Or copy and paste this link into your browser:</p>
              <p style="word-break: break-all;">${verificationUrl}</p>
              <p>This link will expire in 24 hours.</p>
              <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
              </div>
            </div>
          </body>
        </html>
      `,
    })
    logger.info('Verification email sent', { email, userId })
  } catch (error) {
    logger.error('Failed to send verification email', error as Error, { email })
    throw error
  }
}

// Password Reset (Item 2)
export async function sendPasswordResetEmail(email: string) {
  const token = crypto.randomBytes(32).toString('hex')
  const expires = new Date(Date.now() + 60 * 60 * 1000) // 1 hour

  await prisma.verificationToken.upsert({
    where: {
      identifier_token: {
        identifier: `reset-${email}`,
        token: token,
      },
    },
    create: {
      identifier: `reset-${email}`,
      token,
      expires,
    },
    update: {
      expires,
    },
  })

  const resetUrl = `${APP_URL}/auth/reset-password/${token}`

  try {
    await resend.emails.send({
      from: FROM_EMAIL,
      to: email,
      subject: 'Reset your password',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .button {
                display: inline-block;
                padding: 12px 24px;
                background: #dc2626;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 20px 0;
              }
              .warning { background: #fef3c7; padding: 12px; border-radius: 6px; margin: 20px 0; }
              .footer { margin-top: 40px; font-size: 12px; color: #666; }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>Reset Your Password</h1>
              <p>We received a request to reset your password. Click the button below to create a new password:</p>
              <a href="${resetUrl}" class="button">Reset Password</a>
              <p>Or copy and paste this link into your browser:</p>
              <p style="word-break: break-all;">${resetUrl}</p>
              <div class="warning">
                <strong>Security Notice:</strong> This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.
              </div>
              <div class="footer">
                <p>For security, password reset links expire quickly. If this link has expired, you can request a new one.</p>
              </div>
            </div>
          </body>
        </html>
      `,
    })
    logger.info('Password reset email sent', { email })
  } catch (error) {
    logger.error('Failed to send password reset email', error as Error, { email })
    throw error
  }
}

// Approval Notification (Item 19)
export async function sendApprovalNotification(
  userEmail: string,
  agentName: string,
  emailSubject: string,
  approvalUrl: string
) {
  try {
    await resend.emails.send({
      from: FROM_EMAIL,
      to: userEmail,
      subject: `Approval Needed: ${agentName}`,
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .agent-name { color: #0070f3; font-weight: bold; }
              .email-subject { background: #f3f4f6; padding: 12px; border-left: 4px solid #0070f3; margin: 20px 0; }
              .button {
                display: inline-block;
                padding: 12px 24px;
                background: #16a34a;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 20px 0;
              }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>⚠️ Action Required</h1>
              <p>Your agent <span class="agent-name">${agentName}</span> needs your approval for an email response:</p>
              <div class="email-subject">
                <strong>Subject:</strong> ${emailSubject}
              </div>
              <a href="${approvalUrl}" class="button">Review and Approve</a>
              <p>Click the button above to review the draft response and approve or edit it before sending.</p>
            </div>
          </body>
        </html>
      `,
    })
    logger.info('Approval notification sent', { userEmail, agentName })
  } catch (error) {
    logger.error('Failed to send approval notification', error as Error, { userEmail })
  }
}

// Account Deletion Confirmation (Item 5)
export async function sendAccountDeletionEmail(email: string, reactivationToken: string) {
  const reactivationUrl = `${APP_URL}/auth/reactivate/${reactivationToken}`

  try {
    await resend.emails.send({
      from: FROM_EMAIL,
      to: email,
      subject: 'Your account will be deleted',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .warning { background: #fee2e2; padding: 16px; border-radius: 6px; border-left: 4px solid #dc2626; margin: 20px 0; }
              .button {
                display: inline-block;
                padding: 12px 24px;
                background: #0070f3;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 20px 0;
              }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>Account Deletion Scheduled</h1>
              <div class="warning">
                <strong>⚠️ Your account has been scheduled for deletion.</strong>
                <p>Your account and all associated data will be permanently deleted in 30 days.</p>
              </div>
              <p>If this was a mistake, you can reactivate your account at any time within the next 30 days:</p>
              <a href="${reactivationUrl}" class="button">Reactivate My Account</a>
              <p><strong>What happens next:</strong></p>
              <ul>
                <li>Your agents will be disabled immediately</li>
                <li>Your data will be retained for 30 days</li>
                <li>After 30 days, all data will be permanently deleted</li>
                <li>You can reactivate anytime before the 30-day period ends</li>
              </ul>
            </div>
          </body>
        </html>
      `,
    })
    logger.info('Account deletion email sent', { email })
  } catch (error) {
    logger.error('Failed to send account deletion email', error as Error, { email })
  }
}

// 2FA Setup (Item 6)
export async function send2FASetupEmail(email: string) {
  try {
    await resend.emails.send({
      from: FROM_EMAIL,
      to: email,
      subject: 'Two-Factor Authentication Enabled',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .success { background: #d1fae5; padding: 16px; border-radius: 6px; border-left: 4px solid #16a34a; margin: 20px 0; }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>🔒 2FA Enabled</h1>
              <div class="success">
                <strong>Success!</strong> Two-factor authentication has been enabled for your account.
              </div>
              <p>Your account is now more secure. You'll need to provide a verification code from your authenticator app when signing in.</p>
              <p><strong>Important:</strong> Save your backup codes in a secure location. You'll need them to access your account if you lose your authenticator device.</p>
              <p>If you didn't enable 2FA, please contact support immediately.</p>
            </div>
          </body>
        </html>
      `,
    })
  } catch (error) {
    logger.error('Failed to send 2FA setup email', error as Error, { email })
  }
}
