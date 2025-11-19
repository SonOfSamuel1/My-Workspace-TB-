import { test, expect } from '@playwright/test';

test.describe('Approval Queue', () => {
  test('should load approvals page', async ({ page }) => {
    await page.goto('/approvals');

    // Check for main heading
    await expect(page.locator('h1')).toContainText('Approval Queue');

    // Check for description
    await expect(page.locator('text=Review and approve draft responses')).toBeVisible();
  });

  test('should show empty state when no approvals', async ({ page }) => {
    await page.goto('/approvals');

    // Should show empty state
    await expect(page.locator('text=All caught up!')).toBeVisible();
    await expect(page.locator('text=No pending approvals')).toBeVisible();
  });

  test('should navigate from sidebar', async ({ page }) => {
    await page.goto('/dashboard');

    // Click approvals link in sidebar
    await page.click('nav a:has-text("Approvals")');

    // Should navigate to approvals page
    await expect(page).toHaveURL('/approvals');
  });
});

test.describe('Settings Page', () => {
  test('should load settings page with tabs', async ({ page }) => {
    await page.goto('/settings');

    // Check for main heading
    await expect(page.locator('h1')).toContainText('Settings');

    // Check for tabs
    await expect(page.locator('text=Profile')).toBeVisible();
    await expect(page.locator('text=Notifications')).toBeVisible();
    await expect(page.locator('text=Appearance')).toBeVisible();
    await expect(page.locator('text=API Keys')).toBeVisible();
    await expect(page.locator('text=Export/Import')).toBeVisible();
  });

  test('should switch between tabs', async ({ page }) => {
    await page.goto('/settings');

    // Click on Notifications tab
    await page.click('button:has-text("Notifications")');
    await expect(page.locator('text=Email Notifications')).toBeVisible();

    // Click on Export/Import tab
    await page.click('button:has-text("Export")');
    await expect(page.locator('text=Export Configuration')).toBeVisible();
    await expect(page.locator('text=Import Configuration')).toBeVisible();
  });

  test('should have export functionality', async ({ page }) => {
    await page.goto('/settings');

    // Go to Export/Import tab
    await page.click('button:has-text("Export")');

    // Export button should be visible
    const exportButton = page.locator('button:has-text("Export Agents")');
    await expect(exportButton).toBeVisible();
  });
});

test.describe('Analytics Page', () => {
  test('should load analytics page', async ({ page }) => {
    await page.goto('/analytics');

    // Check for main heading
    await expect(page.locator('h1')).toContainText('Analytics');

    // Check for filters
    await expect(page.locator('text=All Agents')).toBeVisible();
    await expect(page.locator('text=Last 30 days')).toBeVisible();

    // Check for metric cards
    await expect(page.locator('text=Total Emails')).toBeVisible();
    await expect(page.locator('text=Avg Response Time')).toBeVisible();
  });

  test('should be able to change time range', async ({ page }) => {
    await page.goto('/analytics');

    // Click time range dropdown
    await page.click('text=Last 30 days');

    // Select different range
    await page.click('text=Last 7 days');

    // Dropdown should update
    await expect(page.locator('text=Last 7 days')).toBeVisible();
  });
});

test.describe('Email Monitor', () => {
  test('should load emails page with filters', async ({ page }) => {
    await page.goto('/emails');

    // Check for main heading
    await expect(page.locator('h1')).toContainText('Email Monitor');

    // Check for filters
    await expect(page.locator('text=Search emails')).toBeVisible();
    await expect(page.locator('text=All Agents')).toBeVisible();
    await expect(page.locator('text=All Tiers')).toBeVisible();
    await expect(page.locator('text=All Statuses')).toBeVisible();
  });

  test('should show empty state when no emails', async ({ page }) => {
    await page.goto('/emails');

    // Should show empty state
    await expect(page.locator('text=No emails found')).toBeVisible();
  });
});
