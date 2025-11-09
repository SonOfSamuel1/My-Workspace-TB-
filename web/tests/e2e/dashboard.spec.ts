import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('should load dashboard page', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for main heading
    await expect(page.locator('h1')).toContainText('Dashboard');

    // Check for stats cards
    await expect(page.locator('text=Total Agents')).toBeVisible();
    await expect(page.locator('text=Pending Approvals')).toBeVisible();
  });

  test('should display empty state when no agents', async ({ page }) => {
    await page.goto('/dashboard');

    // Should show create agent button
    await expect(page.locator('text=Create Your First Agent')).toBeVisible();
  });

  test('should navigate to create agent page', async ({ page }) => {
    await page.goto('/dashboard');

    // Click create agent button
    await page.click('text=Create Agent');

    // Should navigate to new agent page
    await expect(page).toHaveURL('/agents/new');
    await expect(page.locator('h1')).toContainText('Create New Email Agent');
  });

  test('should show sidebar navigation', async ({ page }) => {
    await page.goto('/dashboard');

    // Check sidebar links
    await expect(page.locator('text=Dashboard')).toBeVisible();
    await expect(page.locator('text=Emails')).toBeVisible();
    await expect(page.locator('text=Approvals')).toBeVisible();
    await expect(page.locator('text=Analytics')).toBeVisible();
    await expect(page.locator('text=Agents')).toBeVisible();
    await expect(page.locator('text=Settings')).toBeVisible();
  });
});

test.describe('Dashboard - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should be responsive on mobile', async ({ page }) => {
    await page.goto('/dashboard');

    // Stats cards should stack vertically on mobile
    await expect(page.locator('h1')).toBeVisible();

    // Sidebar should be present
    await expect(page.locator('nav')).toBeVisible();
  });
});
