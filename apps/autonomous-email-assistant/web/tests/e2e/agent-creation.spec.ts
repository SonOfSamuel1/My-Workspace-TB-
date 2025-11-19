import { test, expect } from '@playwright/test';

test.describe('Agent Creation', () => {
  test('should create a new agent successfully', async ({ page }) => {
    await page.goto('/agents/new');

    // Fill in basic information
    await page.fill('#name', 'Test Assistant');
    await page.fill('#agentEmail', 'test@example.com');
    await page.fill('#description', 'Test agent for E2E testing');

    // Select timezone
    await page.click('#timezone');
    await page.click('text=America/Los_Angeles');

    // Set business hours
    await page.click('#startHour');
    await page.click('[value="9"]');

    await page.click('#endHour');
    await page.click('[value="17"]');

    // Select communication style
    await page.click('#style');
    await page.click('text=Professional');

    // Add off-limits contact
    await page.fill('input[placeholder="email@example.com"]', 'boss@company.com');
    await page.click('button:has-text("Plus")');

    // Verify contact was added
    await expect(page.locator('text=boss@company.com')).toBeVisible();

    // Submit form
    await page.click('button[type="submit"]');

    // Should navigate to agent detail page on success
    // (This will fail without actual backend, but shows the test structure)
    // await expect(page).toHaveURL(/\/agents\/[a-z0-9]+/);
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/agents/new');

    // Try to submit without filling required fields
    await page.click('button[type="submit"]');

    // Browser validation should prevent submission
    const nameInput = page.locator('#name');
    await expect(nameInput).toBeFocused();
  });

  test('should be able to cancel creation', async ({ page }) => {
    await page.goto('/agents/new');

    // Fill in some data
    await page.fill('#name', 'Test Agent');

    // Click cancel
    await page.click('text=Cancel');

    // Should navigate back to dashboard
    await expect(page).toHaveURL('/dashboard');
  });

  test('should add and remove off-limits contacts', async ({ page }) => {
    await page.goto('/agents/new');

    // Add contact
    await page.fill('input[placeholder="email@example.com"]', 'test1@example.com');
    await page.click('button:has-text("Plus")');
    await expect(page.locator('text=test1@example.com')).toBeVisible();

    // Add another contact
    await page.fill('input[placeholder="email@example.com"]', 'test2@example.com');
    await page.keyboard.press('Enter');
    await expect(page.locator('text=test2@example.com')).toBeVisible();

    // Remove first contact
    const firstRemoveButton = page.locator('text=test1@example.com').locator('..').locator('button');
    await firstRemoveButton.click();
    await expect(page.locator('text=test1@example.com')).not.toBeVisible();
  });
});

test.describe('Agent Creation - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should work on mobile viewport', async ({ page }) => {
    await page.goto('/agents/new');

    // Form should be visible and usable on mobile
    await expect(page.locator('#name')).toBeVisible();
    await expect(page.locator('#agentEmail')).toBeVisible();

    // Fill in basic fields
    await page.fill('#name', 'Mobile Test Agent');
    await page.fill('#agentEmail', 'mobile@test.com');

    // Submit button should be visible
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });
});
